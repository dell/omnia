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

from pathlib import Path
from logging.handlers import TimedRotatingFileHandler
import logging


def setup_logger(file_name):
    monster_path = Path(__file__).resolve().parent.parent
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    logger = logging.getLogger(file_name)
    formatter = logging.Formatter(log_format)

    log_handler = TimedRotatingFileHandler(filename=f'{monster_path}/log/monster.log', when="midnight", interval=1, backupCount=7)
    log_handler.setLevel(logging.ERROR)
    log_handler.setFormatter(formatter)

    if not logger.handlers:
        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(logging.ERROR)
        stream_handler.setFormatter(formatter)

        logger.addHandler(stream_handler)
        logger.addHandler(log_handler)

    return logger


def get_logger(file_name):
    return setup_logger(file_name)
