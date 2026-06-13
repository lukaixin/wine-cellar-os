# data

本目录用于本地数据库、导入样例和备份。

不要提交真实用户数据库或备份文件。

建议结构：

```text
data/
  wine_cellar.sqlite3       # 本地开发数据库，gitignore
  imports/                  # 导入文件
  sample/                   # 可提交的脱敏样例
  backups/                  # 本地备份，gitignore zip
```
