#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for `loganalysis` module."""

import re
import pytest
from loganalysis import loganalysis


@pytest.mark.parametrize(
    "logfile, expected_lines",
    [("tests/resources/callstack.log", 155), ("tests/resources/unique.log", 50)],
)
@pytest.mark.asyncio
async def test_read_log(logfile: str, expected_lines: int):
    """Test reading log file."""
    lines = [line async for line in loganalysis.read_log(logfile)]
    assert len(lines) == expected_lines


@pytest.mark.parametrize(
    "qualified, expected",
    [
        ("com.company.prod.package.SomeClass.doWork()", "SomeClass.doWork()"),
        (
            "com.company.prod.package.SomeClass$Internal.doWork()",
            "SomeClass$Internal.doWork()",
        ),
        ("AnotherClass.hasNoPackage()", "AnotherClass.hasNoPackage()"),
    ],
)
def test_de_qualify(qualified, expected):
    """Test extracting class.method() from qualified name."""
    expected: str
    assert loganalysis.de_qualify(qualified) == expected


@pytest.mark.parametrize(
    "logfile, expected_lines",
    [("tests/resources/callstack.log", 3), ("tests/resources/unique.log", 0)],
)
@pytest.mark.asyncio
async def test_extract_info(logfile: str, expected_lines):
    """Test extracting info from log file"""
    info = await loganalysis.extract_info(logfile)
    # One line holding the name of the logfile is added by the method.
    assert len(info) == expected_lines + 1
    assert all([line.startswith("###") for line in info])


@pytest.mark.parametrize(
    "logfile, regex, with_timestamp, expected_lines, has_group",
    [
        ("tests/resources/unique.log", r"Shutdown of client", True, 3, False),
        ("tests/resources/unique.log", r"Shutdown of client", False, 3, False),
        ("tests/resources/unique.log", r"([^\s]+) - Shutdown of client", True, 3, True),
        ("tests/resources/unique.log", r"([^\s]+) - Shutdown of client", False, 3,
         True),
    ],
)
@pytest.mark.asyncio
async def test_extract_matches(
    logfile: str, regex: str, with_timestamp: bool, expected_lines: int, has_group: bool
):
    """Test extracting items matching regular expressions."""
    lines = await loganalysis.extract_matches(
        logfile, regex, with_timestamp=with_timestamp
    )
    assert len(lines) == expected_lines
    timestamp_rex = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}")
    matches = [
        timestamp_rex.match(line) is not None for line in lines
    ]
    matches_group = [
        (timestamp_rex.match(line) is not None) == with_timestamp for line in lines
    ]
    assert all(matches_group if has_group else matches)
    if has_group:
        assert all(['ShutDownHookThread:?' in line for line in lines])


@pytest.mark.parametrize(
    "logfile, regex, with_timestamp, expected_lines",
    [
        # No group is always with timestamp
        ("tests/resources/unique.log", r"Shutdown of client", True, 3),
        ("tests/resources/unique.log", r"Shutdown of client", False, 3),
        # With group the with_timestamp flag is evaluated
        ("tests/resources/unique.log", r"([^\s]+) - Shutdown of client", True, 3),
        ("tests/resources/unique.log", r"([^\s]+) - Shutdown of client", False, 1),
    ],
)
@pytest.mark.asyncio
async def test_print_matches_unique(
    logfile: str, regex: str, with_timestamp: bool, expected_lines: int
):
    """Test unique extracting of items matching regular expressions."""
    lines = await loganalysis.print_matches(
        logfile, regex, with_timestamp=with_timestamp, unique=True
    )
    assert len(lines) == expected_lines


@pytest.mark.parametrize(
    "logfile, regex, sort, expected_lines",
    [
        # No group is always with timestamp
        ("tests/resources/unique.log", r"Shutdown of client", False, 3),
        ("tests/resources/unique.log", r"Shutdown of client", True, 3),
    ],
)
@pytest.mark.asyncio
async def test_print_matches_sorted(
    logfile: str, regex: str, sort: bool, expected_lines: int
):
    """Test sorting of extracted items matching regular expressions."""
    lines = await loganalysis.print_matches(
        logfile, regex, sort=sort
    )
    assert len(lines) == expected_lines
    if sort:
        assert lines == sorted(lines)


@pytest.mark.parametrize(
    "logfile, level, expected_items",
    [
        # No group is always with timestamp
        ("tests/resources/unique.log", 'ERROR', 5),
        ("tests/resources/unique.log", ['INFO', 'WARN'], 10),
    ],
)
@pytest.mark.asyncio
async def test_extract_levels_level(
    logfile: str, level: any, expected_items: int
):
    """Test extracting items matching specified levels. Verify levels."""
    level_dict: dict[int: (int, str)] = await loganalysis.extract_levels(
        logfile, level
    )
    assert len(level_dict.keys()) == expected_items
    if isinstance(level, str):
        assert all([level in msg for (_, msg) in
                   level_dict.values()])
    else:
        assert all([any(lvl in msg for (_, msg) in level_dict.values())
                    for lvl in level])


@pytest.mark.parametrize(
    "logfile, level, include_thread, expected_items",
    [
        # No group is always with timestamp
        ("tests/resources/unique.log", 'ERROR', False, 5),
        ("tests/resources/unique.log", 'ERROR', True, 5),
    ],
)
@pytest.mark.asyncio
async def test_extract_levels_thread(
    logfile: str, level: any, include_thread: bool, expected_items: int
):
    """Test extracting items matching specified levels. Verify thread extraction."""
    level_dict: dict[int: (int, str)] = await loganalysis.extract_levels(
        logfile, level, include_thread=include_thread
    )
    assert len(level_dict.keys()) == expected_items
    rex = re.compile(r'^\[[^]]+] ')
    if include_thread:
        assert all([rex.match(msg) is not None for (_, msg) in level_dict.values()])
    else:
        assert all([rex.match(msg) is None for (_, msg) in level_dict.values()])
