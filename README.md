# Install

```bash
$ git submodule update --init --recursive
$ cp sample.toml dev.toml
$ createdb dodo-fighter
# Open dev.toml and edit `url`  in `[database]` to `postgres://localhost:5432/dodo-fighter`
$ pip install -r requirements.txt
```

# Run (debug)

```bash
$ python run.py -d dev.toml
```
