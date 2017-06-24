import datetime
import random as r
import bisect
import itertools
from collections import Counter, namedtuple, defaultdict
from contextlib import contextmanager
from string import Template

availability = {
    'Ethan': {'Sun AM', 'Wed'},
    'Kurt': {'Sun AM', 'Sun PM', 'Wed'},
    'Troy': {'Sun PM', 'Wed'},
    'Bill': {'Sun PM', 'Wed'}
}

class Operators:
    """Information on sound operators"""

    def __init__(self, avail):
        self.availability = self.transform_avail(avail)
        self.names = list(avail.keys())

    def __len__(self): return len(self.names)

    def transform_avail(self, d):
        d = defaultdict(list)
        for name, days in availability.items():
            for day in days:
                d[day].append(name)
        return d

Diagnostic = namedtuple('Diagnostic',
    ['counts', 'rel_weights', 'shift_counts', 'shift_weights'])

def sound_shifts(start_date, end_date):
    """An iterator that emits operating shifts for a given date range"""
    for day in range(start_date.toordinal(), end_date.toordinal()+1):
        full_date = datetime.date.fromordinal(day)
        weekday = full_date.strftime('%A')

        if weekday == 'Sunday':
            yield full_date, 'Sun AM'
            yield full_date, 'Sun PM'
        elif weekday == 'Wednesday':
            yield full_date, 'Wed'

def sound_scheduler(operators, start_date, end_date):
    """Randomly assign operators to a shift"""

    counts, rel_weights = Counter(), Counter(operators.names)
    schedule, diagnostics = [], []
    for date, shift in sound_shifts(start_date, end_date):
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

def main():
    operators = Operators(availability)

    today = datetime.date.today()
    last_day = datetime.date(2017, 9, 1)

    data, schedule = sound_scheduler(operators, today, last_day)

    html_table = '\n'.join(add_indent(table(schedule), 2))
    t = Template(boilerplate)

    filename = 'schedule.html'
    with open(filename, 'w') as f:
        f.write(t.substitute(table=html_table))
        print('{} has been written'.format(filename))

if __name__ == '__main__':
    main()
