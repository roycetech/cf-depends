#!/usr/bin/env python3

import os
from colorama import Fore
from colorama import Style
import re
import traceback
import sys
import filecmp
import pprint


pp = pprint.PrettyPrinter(indent=4)

home_folder = os.environ['HOME']

PROJECT_PATH1 = '{}/projects/mobile-bss'.format(home_folder)
PROJECT_PATH2 = '{}/projects/mobile-bss-legacy'.format(home_folder)

EXCLUDE_PATHS = [
    '_tests',
    '_testing',
    '_systemtests',
    'unittests',
    'integrationtests',
    '_apidocs',
    'sms_receive.cfm',
    'temp_scripts'
]

CHANGED_FILES = set()
CFMAIL_FILES = set()
OCCURENCE_FILES = set()
LEGACY_ONLY_FILES = set()
CFHTTP_FILES = set()
MISSING_INCLUDE_FILES = set()
KEYWORD_MATCHES = {}

LEVEL = 0
INCLUSION = r'\.cf*'
# INCLUSION = '_create_header.cfm|inc_array_calltypes.cfm'

KEYWORDS = [
    r'/nfs/compass/www/secure/ecgateway/billing/bills/',
    r'request.billingdir']


def remove_comments(text):
    pattern = re.compile(r'<!---[\d\D]*?--->')
    return pattern.sub('', text)


def path_included(file_path):
    retval = True
    for excluded in EXCLUDE_PATHS:
        if excluded in file_path:
            retval = False
            break
    if retval:
        retval = re.search(INCLUSION, file_path)
    return retval


def main():
    for root, dirs, files in os.walk(PROJECT_PATH2, onerror=None):
        for filename in files:
            file_path = os.path.join(root, filename)
            try:
                if path_included(file_path):
                    global LEVEL
                    LEVEL = 0
                    for keyword in KEYWORDS:
                        parse_file(keyword, file_path)
            except (IOError, OSError):
                traceback.print_exc(file=sys.stdout)


def parse_file(keyword, file_path, is_sub=False):
    output = ''
    if re.search(INCLUSION, file_path):
        basename = os.path.basename(file_path)
        file_path2 = file_path.replace('mobile-bss-legacy', 'mobile-bss')
        with open(file_path, mode="rb") as f:
            text = str(f.read()).replace('\\r', '').replace('\\t', '\t')
            text = remove_comments(text)
            lines = text.split('\\n')

            for line_number, line in enumerate(lines, 0):
                keyword_matched = re.search(keyword, line)

                if keyword_matched:
                    keyword_files = KEYWORD_MATCHES.get(keyword, [])
                    keyword_files.append(strip_project_path([file_path])[0])
                    KEYWORD_MATCHES[keyword] = keyword_files

                if keyword_matched or is_sub:
                    prefix = ''
                    if is_sub:
                        prefix = '{}SUB {}'.format(Fore.GREEN, LEVEL)
                    if output is '':
                        OCCURENCE_FILES.add(file_path)
                        output += prefix + Fore.YELLOW + file_path + \
                            Style.RESET_ALL + '\n'

                        if os.path.exists(file_path2):
                            if not filecmp.cmp(file_path, file_path2):
                                CHANGED_FILES.add(basename)
                                # print(
                                #     '{}{} Changed!{}'.format(
                                #         Fore.RED,
                                #         basename, Style.RESET_ALL))
                        else:
                            LEGACY_ONLY_FILES.add(file_path)
                            # print('{} Not present in mobile bss'.format(
                            #     file_path))

                    if not is_sub:
                        output += "  {}: {}\n".format(
                            line_number + 1, line.rstrip('\\r'))
            if output:
                # includes = find_keyword(file_path, 'cfinclude', lines)
                find_keyword(file_path, 'cfinclude', lines)
                # if includes:
                #     output += includes

                cfmails = find_keyword(file_path, '<cfmail', lines)
                if cfmails:
                    CFMAIL_FILES.add(file_path)
                    output += cfmails

                cfhttp_calls = find_keyword(file_path, 'cfhttp', lines)
                if cfhttp_calls:
                    CFHTTP_FILES.add(file_path)
                    output += cfhttp_calls

                if not is_sub:
                    print(output.replace(
                        '\\t', '\t').replace('\\r', ''))


def find_keyword(file_path, keyword, lines):
    output = '[[[{}s]]]\n'.format(keyword)
    if keyword == '<cfmail':
        output = '{}[[[{}s]]]{}\n'.format(Fore.RED, keyword, Style.RESET_ALL)

    for line_number, line in enumerate(lines, 0):
        if keyword in line.lower():
            if keyword == 'cfinclude':
                line = line.strip()
            output += "  {}: {}\n".format(line_number + 1, line)

            if keyword == 'cfinclude':
                matcher = re.search(
                    r'(?<=<cfinclude template=")(.*)(?=">)',
                    line)
                if matcher:
                    included_template = matcher.group()
                    folder = os.path.dirname(file_path)
                    import_file = folder + '/' + included_template
                    import_file_clean = evaluate_dotdots(import_file)
                    if os.path.exists(import_file_clean):
                        global LEVEL
                        LEVEL += 1
                        for keyword in KEYWORDS:
                            parse_file(keyword, import_file_clean, True)
                        LEVEL -= 1
                    else:
                        MISSING_INCLUDE_FILES.add(import_file_clean)
                        print('{}Included file not found: {}{}'.format(
                            Fore.RED, import_file_clean, Style.RESET_ALL))

    if keyword == '<cfmail':
        if len(output) > len(keyword) + 17:
            return output
        else:
            return None
    elif len(output) > len(keyword) + 8:
        return output


def evaluate_dotdots(file_path):
    regexpr = r'\w+/\.\./'
    p = re.compile(regexpr)
    new_path = file_path
    while re.search(regexpr, new_path):
        new_path = p.sub('', new_path)
    return new_path


def process_files(file_path):
    pass


def strip_project_path(paths):
    return [x.replace(PROJECT_PATH2, '') for x in paths]


main()


def print_object(title, the_set):
    stripped_set = strip_project_path(the_set)
    print('{}: {}'.format(title, len(the_set)))
    pp.pprint(sorted(stripped_set))


print_object('Changed files', CHANGED_FILES)
print_object('CFMails', CFMAIL_FILES)
print_object('Occurrences', OCCURENCE_FILES)
print_object('Http Calls', CFHTTP_FILES)
print_object('Legacy Only', LEGACY_ONLY_FILES)
print_object('Matches', KEYWORD_MATCHES)
print_object('Missing Include', MISSING_INCLUDE_FILES)
