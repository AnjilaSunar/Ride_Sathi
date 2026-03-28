import pymysql

# Set the version info to satisfy Django's requirement (2.2.1+)
pymysql.version_info = (2, 2, 1, "final", 0)
pymysql.install_as_MySQLdb()
