#!/usr/bin/env python
import argparse
import os
import sys
import subprocess

# Command-line parser
parser = argparse.ArgumentParser(description='Mysql recuperator')
parser.add_argument('--pid', nargs=1, help='PID of Mysql process', required=True)
parser.add_argument('--recover_path', nargs=1, help='Path of directory if you want revover deleted files')
parser.add_argument('--mysql_path', nargs=1, help='Path of mysql directory if you want limit recovery')
parser.add_argument('--touch_files', action='store_true', help='If you want touch deleted files')
parser.add_argument('--export_as_csv', nargs='+', help='List of databases to export require --csv_path argument')
parser.add_argument('--csv_path', nargs=1, help='Path of csv export')
args = parser.parse_args()

# Define default variables
PID = None
RECOVER_PATH = None
MYSQL_PATH = None
TOUCH_REAL_TARGET = args.touch_files
CSV_PATH = None

# Define template for CSV export
CSV_EXPORT = 'SELECT * from {} INTO OUTFILE \'{}\' FIELDS TERMINATED BY \',\' ENCLOSED BY \'"\' LINES TERMINATED BY \'\\n\';'

# Get PID and check if exist
PID = args.pid[0]
PROC_FD_DIR = '/proc/{}/fd'.format(PID)

if not os.path.isdir(PROC_FD_DIR):
    print('Missing {} for process'.format(PROC_FD_DIR))
    sys.exit(1)

# Get deleted file recovery & check if exist
if args.recover_path:
    RECOVER_PATH = args.recover_path[0]

    if not os.path.isdir(RECOVER_PATH):
        print('Missing {} for recovery'.format(RECOVER_PATH))
        sys.exit(1)

# Get mysql data dir to restore only them
if args.mysql_path:
    MYSQL_PATH = args.mysql_path[0]
    MYSQL_PATH_LENGTH = len(MYSQL_PATH)

# Check if CSV export & if directory exist
if args.export_as_csv:
    if not args.csv_path:
        print('Missing --csv_path args')
        sys.exit(1)
    CSV_PATH = args.csv_path[0]

    if not os.path.isdir(CSV_PATH):
        print('Missing {} for csv'.format(CSV_PATH))
        sys.exit(1)


# Check if directory exist & create missing one
def check_recovery_target(target):
    target_splited = target.split('/')[:-1]
    need_existing_directory = '/'.join(target_splited)
    if not os.path.isdir(need_existing_directory):
        check_recovery_target(need_existing_directory)
        os.mkdir(need_existing_directory)


# Check each deleted file
for fd in os.listdir(PROC_FD_DIR):
    # Get each file descriptor for process
    target = os.readlink('{}/{}'.format(PROC_FD_DIR, fd))
    # Handle only deleted one
    if target[-9:] == '(deleted)':
        # Get original target
        real_target = target[:-10]
        handle = True
        # If MYSQL_PATH is defined, filter right files and skip others
        if MYSQL_PATH:
            target_start = target[:MYSQL_PATH_LENGTH]
            if target_start != MYSQL_PATH:
                print('Skip: {}'.format(target))
                handle = False

        if RECOVER_PATH or TOUCH_REAL_TARGET:
            print('=> {}'.format(target))

        # If recover file (content)
        if handle:
            if RECOVER_PATH:
                check_recovery_target('{}{}'.format(RECOVER_PATH, real_target))
                cmd = 'cp {}/{} {}{}'.format(PROC_FD_DIR, fd, RECOVER_PATH, real_target)
                check_output_cp = subprocess.check_output(cmd, shell=True)
                print('File cp: {}'.format(check_output_cp.decode('utf-8')))

        # If touch original file
        if TOUCH_REAL_TARGET:
                check_recovery_target(real_target)
                cmd = 'touch {}'.format(real_target)
                check_output_touch = subprocess.check_output(cmd, shell=True)
                print('File touch: {}'.format(check_output_touch.decode('utf-8')))

# Now export data as CSV for safety (work with a DB list)
for db in args.export_as_csv:
    print('=== Work with: {}'.format(db))
    # Get table list
    cmd = "echo 'show tables;' | mysql {}".format(db)
    check_output_table = subprocess.check_output(cmd, shell=True)
    for table in check_output_table.decode('utf-8').split('\n'):
        # Skip 'Tables_in_' header
        if (table[:10] != 'Tables_in_') and (table != ''):
            # Define files sql, log & err
            sql_file_path = '{}/export_{}_{}.sql'.format(CSV_PATH, db, table)
            sql_file_log = '{}/export_{}_{}.log'.format(CSV_PATH, db, table)
            sql_file_err = '{}/export_{}_{}.err'.format(CSV_PATH, db, table)
            # Create SQL file
            target = '{}/{}_{}.txt'.format(CSV_PATH, db, table)
            # Skip file already exist (mysql fail otherwise)
            if os.path.isfile(target):
                print('{} is already exist, i\'ll skip'.format(target))
            else:
                # Create sql file to export data as CSV
                sql_file = open(sql_file_path, 'w')
                print('File to export SQL data: {}'.format(sql_file_path))
                cmd = CSV_EXPORT.format(table, target, db)
                sql_file.write('{}\n'.format(cmd))
                sql_file.close()

                # Now execute it
                cmd = 'cat {} | mysql {}'.format(sql_file_path, db)
                try:
                    check_output_sqlexec = subprocess.check_output(cmd, shell=True)
                    # If it's works, save log
                    print('Mysql log: {}'.format(check_output_sqlexec.decode('utf-8')))
                    open(sql_file_log, 'w').write(check_output_sqlexec.decode('utf-8'))
                except subprocess.CalledProcessError as e:
                    # Catch error and save it
                    print('Error:')
                    print(e)
                    open(sql_file_err, 'w').write(str(e))
