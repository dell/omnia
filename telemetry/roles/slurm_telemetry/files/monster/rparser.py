"""
MIT License
Copyright (c) 2022 Texas Tech University
Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:
The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

"""
This file is part of MonSter.
Author:
    Jie Li, jie.li@ttu.edu
"""

JSON_COMMA = ','
JSON_COLON = ':'
JSON_LEFTBRACKET = '['
JSON_RIGHTBRACKET = ']'
JSON_LEFTBRACE = '{'
JSON_RIGHTBRACE = '}'
JSON_QUOTE = '"'

JSON_QUOTE = '"'
JSON_WHITESPACE = [' ', '\t', '\b', '\n', '\r']
JSON_SYNTAX = [JSON_COMMA, JSON_COLON, JSON_LEFTBRACKET, JSON_RIGHTBRACKET,
               JSON_LEFTBRACE, JSON_RIGHTBRACE]

FALSE_LEN = len('false')
TRUE_LEN = len('true')
NULL_LEN = len('null')


def lex_string(string):
    json_string = ''

    if string[0] == JSON_QUOTE:
        string = string[1:]
    else:
        return None, string

    for c in string:
        if c == JSON_QUOTE:
            return json_string, string[len(json_string)+1:]
        else:
            json_string += c

    # raise Exception('Expected end-of-string quote')
    return json_string, ''
    

def lex_number(string):
    json_number = ''

    number_characters = [str(d) for d in range(0, 10)] + ['-', 'e', '.']

    for c in string:
        if c in number_characters:
            json_number += c
        else:
            break

    rest = string[len(json_number):]

    if not len(json_number):
        return None, string

    if '.' in json_number:
        return float(json_number), rest

    return int(json_number), rest


def lex_bool(string):
    string_len = len(string)

    if string_len >= TRUE_LEN and \
       string[:TRUE_LEN] == 'true':
        return True, string[TRUE_LEN:]
    elif string_len >= FALSE_LEN and \
         string[:FALSE_LEN] == 'false':
        return False, string[FALSE_LEN:]

    return None, string


def lex_null(string):
    string_len = len(string)

    if string_len >= NULL_LEN and \
       string[:NULL_LEN] == 'null':
        return True, string[NULL_LEN]

    return None, string


def lex(string):
    tokens = []

    while len(string):
        json_string, string = lex_string(string)
        if json_string is not None:
            tokens.append(json_string)
            continue

        json_number, string = lex_number(string)
        if json_number is not None:
            tokens.append(json_number)
            continue

        json_bool, string = lex_bool(string)
        if json_bool is not None:
            tokens.append(json_bool)
            continue

        json_null, string = lex_null(string)
        if json_null is not None:
            tokens.append(None)
            continue

        if string[0] in JSON_WHITESPACE:
            string = string[1:]
        elif string[0] in JSON_SYNTAX:
            tokens.append(string[0])
            string = string[1:]
        else:
            raise Exception('Unexpected character: {}'.format(string[0]))
        
        # print(tokens)

    return tokens


def parse_array(tokens):
    # print("PARSE ARRAY: ")
    # print(tokens)
    json_array = []

    if tokens:
        t = tokens[0]
        if t == JSON_RIGHTBRACKET:
            return json_array, tokens[1:]

        while True:
            json, tokens = parse(tokens)
            json_array.append(json)

            # print(f'Json array: {json_array}')

            if tokens:
                t = tokens[0]
                if t == JSON_RIGHTBRACKET:
                    return json_array, tokens[1:]
                elif t != JSON_COMMA:
                    raise Exception('Expected comma after object in array')
                else:
                    tokens = tokens[1:]
            else:
                return json_array, None
    return None, None
    # raise Exception('Expected end-of-array bracket')


def parse_object(tokens):
    # print("PARSE OBJECT: ")
    # print(tokens)
    json_object = {}

    if tokens:
        t = tokens[0]

        if t == JSON_RIGHTBRACE:
            return json_object, tokens[1:]

        while True:
            if tokens:
                json_key = tokens[0]
                # print(f'Json key: {json_key}')

                if type(json_key) is str:
                    tokens = tokens[1:]
                else:
                    raise Exception('Expected string key, got: {}'.format(json_key))

                if tokens:
                    if tokens[0] != JSON_COLON:
                        raise Exception('Expected colon after key in object, got: {}'.format(t))

                    json_value, tokens = parse(tokens[1:])
                    # print(f'Json value: {json_value}')

                    json_object[json_key] = json_value

                    # print(f'Json object: {json_object}')

                if tokens:
                    t = tokens[0]
                    if t == JSON_RIGHTBRACE:
                        return json_object, tokens[1:]
                    elif t != JSON_COMMA:
                        raise Exception('Expected comma after pair in object, got: {}'.format(t))

                    tokens = tokens[1:]
            else:
                return json_object, None
    return None, None
    # raise Exception('Expected end-of-object brace')

def parse(tokens):
    if tokens:
        t = tokens[0]

        # print("PARSE: ")
        # print(tokens)

        if t == JSON_LEFTBRACKET:
            return parse_array(tokens[1:])
        elif t == JSON_LEFTBRACE:
            return parse_object(tokens[1:])
        else:
            return t, tokens[1:]
    else:
        return None, None


def report_parser(string):
    tokens = lex(string)
    return parse(tokens)[0]
