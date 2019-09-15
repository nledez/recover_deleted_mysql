# If you want to test it

```
vagrant up
vagrant ssh
# Now you are in.
# Careful always check you are in vagrant@ubuntu-bionic

# It's time to install data
git clone https://github.com/datacharmer/test_db.git
cd test_db
cat employees.sql | sudo mysql

# Check if it works
echo 'show databases;' | sudo mysql

# We need a backup for later
sudo service mysql stop
sudo mkdir /backup
sudo rsync -av /var/lib/mysql/ /backup/
sudo chmod 777 /backup
sudo service mysql start
sudo bash /vagrant/read_all_data.sh

# Now it's time to destroy your database.
sudo find /var/lib/mysql -type f -exec rm {} \;
sudo find /var/lib/mysql -type d -exec rmdir {} \;
# Ouupppsss
sudo ls -la /var/lib/mysql/
# Check if you have made a real fucking shit:
echo 'show databases;' | sudo mysql
```

## Instructions and why it can work

- Never stop mysql never, never, never & never
- Never try a mysqldump when using this tool, never, again
- Identify process mysql `ps ax | grep [m]ysqld`
- You have only one process & get the PID
- Save PID `MYSQL_PID=2530`
- Check how we can recover data `sudo lsof -p $MYSQL_PID`
- You can see all '(deleted)' files
- And as long as Mysql is not stopped, we can recover the data

In summary:

```
sudo mkdir /recover
ps ax | grep [m]ysqld
MYSQL_PID=2530
sudo lsof -p $MYSQL_PID
```

## And now, let the magic operate

### Show help

```
$ sudo /vagrant/recover_deleted_mysql.py --help
usage: recover_deleted_mysql.py [-h] --pid PID [--recover_path RECOVER_PATH]
                                [--mysql_path MYSQL_PATH] [--touch_files]
                                [--export_as_csv EXPORT_AS_CSV [EXPORT_AS_CSV ...]]
                                [--csv_path CSV_PATH]

Mysql recuperator

optional arguments:
  -h, --help            show this help message and exit
  --pid PID             PID of Mysql process
  --recover_path RECOVER_PATH
                        Path of directory if you want revover deleted files
  --mysql_path MYSQL_PATH
                        Path of mysql directory if you want limit recovery
  --touch_files         If you want touch deleted files
  --export_as_csv EXPORT_AS_CSV [EXPORT_AS_CSV ...]
                        List of databases to export require --csv_path
                        argument
  --csv_path CSV_PATH   Path of csv export
```

### Recover deleted files

```
sudo /vagrant/recover_deleted_mysql.py --pid $MYSQL_PID --mysql_path /var/lib/mysql --recover_path /recover
# Check with `sudo find /recover -ls`
```

### Extract data for safety

```
sudo /vagrant/recover_deleted_mysql.py --pid $MYSQL_PID --mysql_path /var/lib/mysql --touch_files
sudo chown -R mysql:mysql /var/lib/mysql
# Now you can list databases:
echo 'show databases;' | sudo mysql
# But the databases have now tables
echo 'show tables;' | sudo mysql employees
# We need .frm to have tables structures
cd /backup/
sudo find * -name '*.frm' -exec cp {} /var/lib/mysql/{} \;
sudo chown -R mysql:mysql /var/lib/mysql
echo 'show tables;' | sudo mysql employees
# Now you can request database. But not a mysqldump :(
# DO NOT TRY A mysqldump
echo 'SHOW VARIABLES LIKE "secure_file_priv";' | sudo mysql # Get /var/lib/mysql-files/
sudo /vagrant/recover_deleted_mysql.py --pid $MYSQL_PID --csv_path /var/lib/mysql-files --export_as_csv employees
```

### Put recover data back

```
sudo rsync -av /recover/var/lib/mysql/ /var/lib/mysql/
sudo service mysql stop
sudo chown -R mysql:mysql /var/lib/mysql
sudo service mysql start
sudo mysqlcheck --all-databases
sudo mysql_upgrade
sudo service mysql restart
cd
sudo mysqldump employees > employees.sql
```
