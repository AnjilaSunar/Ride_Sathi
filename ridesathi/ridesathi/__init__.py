import pymysql

# Satisfy Django's mysqlclient version check (we use PyMySQL as drop-in)
pymysql.version_info = (2, 2, 1, "final", 0)
pymysql.install_as_MySQLdb()
