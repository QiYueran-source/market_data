# 接口说明  
db下的api目录，提供对每一个表的接口，用于获取表的数据。   
使用sshfs挂载db目录，在本地获取db目录数据。  
统一返回pandas的DataFrame。    

由于sshfs仅挂载db目录，不挂载schema目录，
所以api中访数据无法通过schema确认结构，需要手动确认。  
