import datetime
import os, glob, sys
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
        """Read an array of tables from TOML"""

        d = {}
        for operator in array['operators']:
            k, v = operator['name'], operator['shifts']
            d[k] = v

        return cls(d)

    def transform_avail(self, old_d):
        """Transpose the dictionary (swap keys and values)"""

        d = defaultdict(list)
        for name, days in old_d.items():
            for day in days:
                d[day].append(name)
        return d

class Date(datetime.date):
    """Extend datetime.date to have an additional constructor"""

    @classmethod
    def fromstring(cls, s, format_string):
        dt = datetime.datetime.strptime(s, format_string).toordinal()
        return cls.fromordinal(dt)

# Diagnostic is used to to store important variables in order to verify that the
# relative-weighting of operators is working correctly.
Diagnostic = namedtuple('Diagnostic',
    ['counts', 'rel_weights', 'shift_counts', 'shift_weights'])

# TimeData is used to hold the dates for the schedule and what shifts are needed
# on what weekdays.
TimeData = namedtuple('TimeData', ['first_date', 'last_date', 'shifts'])

def sound_shifts(time_data):
    """An generator that emits operating shifts for a given date range"""

    def dates(first, last):
        """Helper generator to seperate the ordinal date switching"""

        first_num, last_num = first.toordinal(), last.toordinal()
        for i in range(first_num, last_num+1):
            yield datetime.date.fromordinal(i)

    for full_date in dates(time_data.first_date, time_data.last_date):
        weekday = full_date.strftime('%A')

        shifts = []
        try:
            shifts = time_data.shifts[weekday]
        except KeyError:
            # If not correct weekday, go to next weekday
            pass

        # for loop doesn't loop if shifts is an empty list
        for shift in shifts:
            yield full_date, shift

def sound_scheduler(operators, time_data):
    """Randomly assign operators to a shift

    the output is a list of strings representing the rows of a table where each
    row is of the form [date, shift, operator]

    To try to maintain a uniform distribution, the algorithm assigns  relative
    weights to each operator.  After every iteration, the relative weights are
    updated so that the last operator picked is less likely to be picked again.
    The weights are also scaled after each iteration to keep the weights from
    growing large.

    """

    counts, rel_weights = Counter(), Counter(operators.names)
    schedule, diagnostics = [], []
    for date, shift in sound_shifts(time_data):
        pop = operators.availability[shift]
        weights = [rel_weights[name] for name in pop]

        # Used only for tracking variables; not used in algorithm
        diagnostics.append(Diagnostic(counts, rel_weights, pop, weights))

        # *sound_person* is a single string
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
    """Randomly pick an item from a list based on the item's relative weight

    *population* is a list of items
    *rel_weights* is a list of relative weights for each item in *population*

    """

    cum_weights = list(itertools.accumulate(rel_weights))
    x = r.random() * cum_weights[-1]
    ix = bisect.bisect(cum_weights, x)
    return population[ix]

@contextmanager
def tags(name, table, indent_level=0):
    """Surround with open and closing html tags

    *name* is the tag name
    *table* is a list of strings that will be concatenated
    *indent_level* is how many levels to indent the tags

    """

    indent = '\t' * indent_level
    table.append('{}<{}>'.format(indent, name))
    yield
    table.append('{}</{}>'.format(indent, name))

def create_table(data, head=[]):
    """Generate an html table

    *data* is a list of lists
    the output is a list of strings representing html table

    """

    indent, n_indents = '\t', 5
    table = []
    for row in data:
        with tags('tr', table, n_indents):
            cells = ''.join(['<td>{}</td>'.format(cell) for cell in row])
            table.append(indent*(n_indents+1) + cells)

    return table

def add_indent(string_list, level, indent_char='\t'):
    return [indent_char*level + item for item in string_list]

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

class HtmlParts:
    def __init__(self, schedule_list, config):
        self.sub_table = {
            'css': '',
            'title': config['title'],
            'schedule_table': self.schedule_table(schedule_list),
            'contacts_table': self.contacts_table(config['operators']),
            'notes': self.notes(config['notes'])
        }

    def css(self, filepath):
        with open(filepath, 'r') as f:
            lines = f.readlines()
        lines = add_indent(lines, 3)
        return ''.join(lines).rstrip()

    def schedule_table(self, lines):
        return '\n'.join(create_table(lines))

    def contacts_table(self, operators):
        lines = [(op['name'], op['phone']) for op in operators]
        return '\n'.join(create_table(lines))

    def notes(self, lines):
        with_tags = ['<li>{}</li>'.format(line) for line in lines]
        with_tags = add_indent(with_tags, 5)
        return '\n'.join(with_tags)


def pyinstaller_dir(filepaths):
    bundle_dir = ''
    if getattr(sys, 'frozen', False):
            # we are running in a bundle
            bundle_dir = sys._MEIPASS
            sys.path.insert(0,bundle_dir)
    d = {}
    for k, v in filepaths.items():
        d[k] = os.path.join(bundle_dir, v)
    return d

def main():
    from pprint import pprint

    args = parse()
    config = parse_config(args.toml_file)

    # format string example: 2017-01-01
    f = '%Y-%m-%d'
    today = Date.fromstring(config['start_date'], f)
    last_day = Date.fromstring(config['end_date'], f)
    time_data = TimeData(today, last_day, config['shifts'])
    operators = Operators.fromconfig(config)

    data, schedule = sound_scheduler(operators, time_data)

    dir_paths = {'data': 'html-template', 'font': 'Overpass'}
    paths = {
        'css': ['{data}', 'schedule-template.css'],
        'html': ['{data}', 'schedule-template.html'],
        'font_normal': ['{data}', '{font}', '{font}-Regular.ttf'],
        'font_bold': ['{data}', '{font}', '{font}-Bold.ttf'],
    }

    for k in paths:
        paths[k] = os.path.join(*paths[k]).format_map(dir_paths)
    paths.update(dir_paths)
    paths = pyinstaller_dir(paths)

    html_parts = HtmlParts(schedule, config)
    sub_dict = html_parts.sub_table
    css_template = Template(html_parts.css(paths['css']))
    font_urlify = '{font}'.format_map(paths).replace(' ', '+')
    sub_dict['css'] =  css_template.substitute(**paths, font_urlify=font_urlify)

    with open(paths['html'], 'r') as f:
        lines = f.readlines()
    string = ''.join(lines).strip()
    html_template = Template(string)

    toml_name = os.path.splitext(args.toml_file)[0]
    name = toml_name + '-schedule'
    n = len(glob.glob(name + '*.html'))
    filename = '{}-{:02}.html'.format(name, n)
    
    with open(filename, 'w') as f:
        f.write(html_template.substitute(**sub_dict))
        print('{} has been written'.format(filename))

if __name__ == '__main__':
    main()
