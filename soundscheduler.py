import datetime
import random as r
import bisect
import itertools
from collections import Counter, namedtuple, defaultdict
from contextlib import contextmanager
from string import Template
import argparse

import pytoml as toml

class Operators:
    """Information on sound operators"""

    def __init__(self, avail):
        self.availability = self.transform_avail(avail)
        self.names = list(avail.keys())

    def __len__(self): return len(self.names)

    @classmethod
    def fromconfig(cls, array):
        d = {}
        for operator in array['operators']:
            k, v = operator['name'], operator['shifts']
            d[k] = v

        return cls(d)

    def transform_avail(self, old_d):
        d = defaultdict(list)
        for name, days in old_d.items():
            for day in days:
                d[day].append(name)
        return d

Diagnostic = namedtuple('Diagnostic',
    ['counts', 'rel_weights', 'shift_counts', 'shift_weights'])

TimeData = namedtuple('TimeData', ['first_date', 'last_date', 'shifts'])

def sound_shifts(time_data):
    """An iterator that emits operating shifts for a given date range"""

    def dates(first, last):
        first_num, last_num = first.toordinal(), last.toordinal()
        for i in range(first_num, last_num+1):
            yield datetime.date.fromordinal(i)

    for full_date in dates(time_data.first_date, time_data.last_date):
        weekday = full_date.strftime('%A')

        try:
            shifts = time_data.shifts[weekday]
        except KeyError: shifts = []

        for shift in shifts:
            yield full_date, shift

def sound_scheduler(operators, time_data):
    """Randomly assign operators to a shift"""

    counts, rel_weights = Counter(), Counter(operators.names)
    schedule, diagnostics = [], []
    for date, shift in sound_shifts(time_data):
        pop = operators.availability[shift]
        weights = [rel_weights[name] for name in pop]

        diagnostics.append(Diagnostic(counts, rel_weights, pop, weights))

        sound_person = choices(pop, weights)
        counts.update((sound_person,))

        diff = set(operators.names) - set((sound_person,))
        for name in diff:
            rel_weights[name] *= 10

        lo = min(rel_weights.values())
        for k in rel_weights.keys():
            rel_weights[k] //= lo

        line = [date.strftime('%b %d'), shift, sound_person]
        schedule.append(line)


    return (counts, diagnostics), schedule

def choices(population, rel_weights):
    cum_weights = list(itertools.accumulate(rel_weights))
    x = r.random() * cum_weights[-1]
    ix = bisect.bisect(cum_weights, x)
    return population[ix]

@contextmanager
def tags(name, table, indent_level=0):
    indent = '\t' * indent_level
    table.append('{}<{}>'.format(indent, name))
    yield
    table.append('{}</{}>'.format(indent, name))

def table(data, head=[]):
    """Generate an html table
    data is a list of lists
    output is a list of strings representing html
    """
    indent = '\t'
    table = []
    with tags('table', table):
        for row in data:
            with tags('tr', table, 1):
                cells = ''.join(['<td>{}</td>'.format(cell) for cell in row])
                table.append(indent*2 + cells)

    return table

def add_indent(string_list, level, indent_char='\t'):
    return [indent_char*level + item for item in string_list]


boilerplate = '''
<!DOCTYPE html>
<html>
    <head>
        <style>
            @import url("https://fonts.googleapis.com/css?family=Overpass");
            body {
                font-family: "Overpass", sans-serif;
                font-size: 12pt;
            }
            table {
                width: 50%;
                border: 1px solid;
                border-collapse: collapse;
            }
            tr:nth-child(even) {
                background-color: #dddddd;
            }
        </style>
        <meta charset="utf-8">

        <title>Woodcrest Sound Schedule</title>
    </head>
    <body>
$table
    </body>
</html>
'''

def parse():
    parser = argparse.ArgumentParser(description='Create a schedule.')
    parser.add_argument('toml_file', type=str,
                        help='file path to TOML configuration file')
    args = parser.parse_args()

    return args

def parse_config(filepath):
    with open(filepath, 'r') as f:
        c = toml.load(f)

    return c

def main():
    from pprint import pprint

    args = parse()
    config = parse_config(args.toml_file)


    today = datetime.date.today()
    last_day = datetime.date(2017, 9, 1)
    time_data = TimeData(today, last_day, config['shifts'])
    operators = Operators.fromconfig(config)

    data, schedule = sound_scheduler(operators, time_data)

    html_table = '\n'.join(add_indent(table(schedule), 2))
    t = Template(boilerplate)

    filename = 'schedule.html'
    with open(filename, 'w') as f:
        f.write(t.substitute(table=html_table))
        print('{} has been written'.format(filename))

if __name__ == '__main__':
    main()
