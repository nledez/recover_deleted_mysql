#!/bin/bash
DATABASES=`echo 'show databases;' | mysql | grep -vE '^(Database|information_schema|performance_schema|sys)$'`

for db in ${DATABASES}; do
	TABLES=`echo 'show tables;' | mysql ${db} | grep -vE '^Tables_in_'`
	for table in ${TABLES}; do
		echo "select * from ${table}" | mysql ${db} > /dev/null
	done
done
