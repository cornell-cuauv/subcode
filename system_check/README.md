This is the current folder for the auv-syscheck command that executes tests to be run on the sub.
The testing code works in the following fashion:

syscheck.py: syscheck.py is the head of command. It runs the tests that are selected by test.py and prints out the results. test.py selects the tests from filters passed by syscheck.py such as the environment and whether it's an autonomous run or not.
syscheck.py also takes in a few command line arguments to indicate which tests to run and how to display the output.

test.py: test.py is a test selector. It looks through all of the tests in tests.py and takes the tests that fit the criteria it's searching for. This criteria of course comes from syscheck.py, but test.py translates it into a flag to signify if a test should be run.

tests.py: tests.py actually holds all of the tests. The tests are grouped, and some of them have headers to indicate under which conditions they should be run. If a test should be run regardless of condition, do not give it a header. This is where to go to write new tests.

For any further questions, reach out to Oliver Matte(ojm23)
