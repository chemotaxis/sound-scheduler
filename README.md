# Sound Scheduler

This is a command line tool to make a printable schedule of people operating the
sound board for services.

## Using Sound Scheduler

Sound Scheduler is configured using a TOML file and is required to run Sound Scheduler.  An `example.toml` file is provided for use as a template.  Feel free to copy and rename the `example.toml` file to create custom schedules.

On Mac:

```
./soundscheduler example.toml
```

This will create an html schedule in the current directory.

Sound Scheduler will try to use each operator equally over the time period
given.

For additional help:

```
./soundscheduler --help
```


If you want to run Sound Scheduler from the Python source, you first need to
install `pytoml`.  Then, run this:

```
python -m soundscheduler example.toml
```

## Building Sound Scheduler

If you want to build an executable, install `pyinstaller` as well as `pytoml`.

On Mac:

```
sh build-soundscheduler.sh
```
