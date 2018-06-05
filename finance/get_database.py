import sqlite3

dbConn = sqlite3.connect('info.db')
if 1==1:
	dbConn.execute('''
					create table tbhave
				   (id integer not null,
				    name text,
					shares integer not null,
					price text,
					total text,
					symbol text not null)'''
					)
	dbConn.execute('''
					create table tbhis
				   (id integer not null,
				    shares integer not null,
					price text not null,
					symbol text not null,
					transacted datetime default CURRENT_TIMESTAMP)'''
				  )