import datetime
import os, glob
import random as r
import bisect
import itertools
from collections import Counter, namedtuple, defaultdict
from contextlib import contextmanager
from string import Template
import argparse

import pytoml as toml

PROG_NAME = 'soundscheduler'
__version__ = '0.1.0'

# format string example: 2017-01-01
DATE_FORMAT = '%Y-%m-%d'

class Operators:
    """Information on sound operators"""

    def __init__(self, avail, exceptions):
        self.availability = self.transform_avail(avail)
        self.names = list(avail.keys())
        self.exceptions = exceptions

    def __len__(self): return len(self.names)

    @classmethod
    def fromconfig(cls, array):
        """Read an array of tables from TOML"""

        def read_exceptions(operator):
            """Specify date exceptions for individual operators

            You can enumerate which shifts are not available by doing this:
                [date, shift]

            Or specify that the whole day is unavailable:
                [date]
            """
            exceptions = set()
            try:
                exceptions = operator['exceptions']
            except KeyError:
                # operator does not have an exception, so return empty set
                return exceptions

            new_e = set()
            for exception in exceptions:
                if len(exception) > 1:
                    new_e.add(tuple(exception))
                else:
                    # whole day is an exception; therefore add all shifts
                    date = exception[0]
                    weekday = Date.fromstring(date, DATE_FORMAT).strftime('%A')
                    shifts = array['shifts'][weekday]
                    for shift in shifts:
                        new_e.add((date, shift))
            exceptions = new_e
            return exceptions

        d, e = {}, defaultdict(set)
        for operator in array['operators']:
            name, shifts = operator['name'], operator['shifts']
            if shifts:
                d[name] = shifts

            exceptions = read_exceptions(operator)
            for exception in exceptions:
                e[exception].add(name)

        return cls(d, e)

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
    last_person = ''
    for date, shift in sound_shifts(time_data):
        pop = operators.availability[shift]
        k = (date.strftime(DATE_FORMAT), shift)

        if k in operators.exceptions:
            pop = set(pop) - operators.exceptions[k]
            pop = list(pop)

        if len(pop) > 1:
            pop = list(set(pop) - set([last_person]))
        weights = [rel_weights[name] for name in pop]

        # Used only for tracking variables; not used in algorithm
        diagnostics.append(
            Diagnostic(counts.copy(), rel_weights.copy(), pop, weights))

        # *sound_person* is a single string
        sound_person = choices(pop, weights)
        last_person = sound_person
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
    parser.add_argument('toml_file',
        type=str,
        help='file path to TOML configuration file')
    parser.add_argument('--version',
        action='version', version='{} {}'.format(PROG_NAME, __version__),
        help='show program\'s name and version number')
    parser.add_argument('-n',
        type=int, default=1,
        help='number of schedules to create')

    args = parser.parse_args()

    return args

def parse_config(filepath):
    with open(filepath, 'r') as f:
        c = toml.load(f)

    return c

class HtmlParts:
    """Combine all parts into properly formatted html and css

    Mainly adds newline characters and a couple indents
    """

    def __init__(self, schedule_list, config):
        self.sub_table = {
            'css': '',
            'title': config['title'],
            'subtitle': '',
            'schedule_table': self.schedule_table(schedule_list),
            'contacts_table': self.contacts_table(config['operators']),
            'notes': self.notes(config['notes'])
        }

    @staticmethod
    def add_year(start, end):
        year = str(start)
        if start != end:
            year = '/'.join(map(str, [start, end]))
        return year

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

def main(args):
    config = parse_config(args.toml_file)

    today = Date.fromstring(config['start_date'], DATE_FORMAT)
    last_day = Date.fromstring(config['end_date'], DATE_FORMAT)
    time_data = TimeData(today, last_day, config['shifts'])
    operators = Operators.fromconfig(config)

    data, schedule = sound_scheduler(operators, time_data)

    dir_paths = {'data': 'html-template', 'font': 'Overpass'}
    paths = {
        'css': ['{data}', 'schedule-template.css'],
        'html': ['{data}', 'schedule-template.html'],
        'font_normal': ['{data}', '{font}', '{font}-Regular.ttf'],
        'font_bold': ['{data}', '{font}', '{font}-ExtraBold.ttf'],
    }

    # convert lists to file paths
    for k in paths:
        paths[k] = os.path.join(*paths[k]).format_map(dir_paths)
    paths.update(dir_paths)

    html_parts = HtmlParts(schedule, config)
    sub_dict = html_parts.sub_table
    sub_dict['subtitle'] = html_parts.add_year(today.year, last_day.year)
    css_template = Template(html_parts.css(paths['css']))
    font_urlify = '{font}'.format_map(paths).replace(' ', '+')
    sub_dict['css'] = css_template.substitute(**paths, font_urlify=font_urlify)
    sub_dict['version'] = '{} {}'.format(PROG_NAME, __version__)

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
    args = parse()
    for _ in range(args.n):
        main(args)
