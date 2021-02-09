# Sound Scheduler

This is a command line tool to make a printable schedule of people operating the
sound board for services.  It creates an html page that can be viewed or printed
in a browser.

## Using Sound Scheduler

For now, you will need a version of Python installed.  The only other dependency is `pytoml`.

```shell
pip install pytoml
```

Next, configure your schedule using a TOML file.  Sound Scheduler is configured
using a TOML file and is required to run Sound Scheduler.  An `example.toml`
file is provided for use as a template.  Feel free to copy and rename the
`example.toml` file to create custom schedules.

Finally, create schedules using the command below:

```shell
python -m soundscheduler example.toml
```

Some optional flags are available:

```shell
python -m soundscheduler -h
```

### Changing the html or css

The html template and css files are located in the `html-template` folder.

## Create a binary

Optionally, you can build an executable file that can run on a computer that
doesn't have Python installed.  You will need to build a separate executable on
each OS you plan to run the program.  In other words, you can't run on Windows
using an executable you built on MacOS.

Install `pyinstaller`:

```shell
pip install pyinstaller
```

Execute the following command to build the executable file:

```shell
pyinstaller --onefile --dist . --specpath build_other soundscheduler.py
```

The executable file will be created in the current directory.  Run the
executable in the root directory of this project or run it wherever the
`html-template` folder and TOML file are located.
