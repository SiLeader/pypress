# PyPress - Static Markdown Site Generator and Server

&copy; 2019 SiLeader and Cerussite.

## features
+ static site generator and server
+ Markdown support
+ Search (index search)
  + N-Gram support

## configuration file
### server configuration
```yaml
search:  # search api server
  enabled: true
content:  # content server
  enabled: true

host: localhost
port: 8080
```

### generator configuration
```yaml
indexes:
  enabled: true
  type: ngram
  n: 2
  point:
    title: 2
    content: 1
  file:
    type: yaml  # yaml, pickle, or json
highlight: default  # syntax highlight css theme
```

## contents directory structure
+ config/
  + server.yml
  + generator.yml
+ page/
  + frame.html (page frame)
  + contents/
    + *.md
    + other resources (e.g. *.css, *.png)
+ generated/
  + contents/ (contents root)
  + indexes.{yml, json, pickle}
+ temporary/ (temporary directory)

## dependencies
+ [Markdown](https://pypi.org/project/Markdown/)
+ [PyYAML](https://pypi.org/project/PyYAML/)
+ [Pygments](https://pypi.org/project/Pygments/)
+ [py-gfm](https://pypi.org/project/py-gfm/)
+ [Jina2](https://pypi.org/project/Jinja2/)
+ [beautifulsoup4](https://pypi.org/project/beautifulsoup4/)
+ [richleland/pygments-css](https://github.com/richleland/pygments-css)

## license
Mozilla Public License 2.0
