# 任务  
任务定义在jobs目录下。   
功能上，每一个table对应一个job，这个job通过访问不同的provider获取数据，通过buffer写入db  
组织上，每一个db对应一个目录，每一个表对应update_xxx_table.py文件，用于更新该表的数据    