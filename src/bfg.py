#! /usr/bin/env python3
# coding: utf-8

"""BrainFucking Gone - A simple BrainFuck interpreter."""

__version__    = "0.1.0"
__license__    = "MIT"
__author__     = "Alexandre Martos"
__maintainer__ = "Alexandre Martos"
__email__      = "contact@amartos.fr"
__copyright__  = "Copyright 2023 " + __author__ + " <{}>".format(__email__)
__status__     = "Production"

import sys, argparse

class BrainFuckingGoneError(Exception):
    """Interpreter exceptions."""

class BrainFuckingGone:
    """A simple BrainFuck interpreter.

    Example:
    >>> bfg = BrainFuckingGone()
    >>> # either run in interactive mode with
    >>> bfg.run()
    >>> # or run scripts with
    >>> bfg.run(["my/script", "my/other.script"])
    """

    def __init__(self):
        """Initialize the class."""

        self.count  = 0
        self.memmax = 30 * 1000
        self.minmax = [0,255]
        self.errmsg = "{} at instruction #{} ('{}'): {}"
        self.stdout = None
        self.remain = None
        self.ins    = None
        self.inslen = 0
        self.keep   = False
        self.strict = False
        self.debug  = False
        self.keep   = False
        self.lang   = {
            "loops": { "left": "[", "right": "]", "func": self.loop  },
            "ptrs":  { "left": "<", "right": ">", "func": self.ptr   },
            "bytes": { "left": "-", "right": "+", "func": self.byte  },
            "ios":   { "left": ",", "right": ".", "func": self.inout },
            "comments": { "left": "#", "right": "\n", "func": self.ignoreUntil }
        }
        self.action = {}
        for k,i in self.lang.items():
            self.action[i.get("left")]  = i.get("func")
            self.action[i.get("right")] = i.get("func")

    def run(self, files = None, persistent = False, debug = False, strict = False):
        """Run the interpreter.

        Args:
            files: A list of scripts paths to run.
            persistent: A boolean indicating to make the memory
                persistent between command executions.
            debug: A boolean activating debug mode if True.
            strict: A boolean activating strict mode if True. In
                strict mode, the memory is limited by the language
                standard values.
        """

        shell = True
        if args:
            shell = not files or len(files) == 0
            self.strict = strict
            # The shell is always in debug mode and with memory
            # persistence. But we do not want to wait for the output,
            # thus it is not delayed in this case.
            self.debug  = debug or shell
            self.stdout = None if not self.debug or shell else ""
            self.keep   = persistent or shell
            programs    = self.script(files)

        self.reset(True)
        self.ins = ""
        while(shell or len(files) > 0):
            if shell: self.ins = self.shell()
            else:
                self.ins = self.script(files)
                files    = files[1:]
            if self.ins is not None:
                self.execute()
        if self.stdout is not None:
            print("Output:", file=sys.stderr)
            print(self.stdout)
        else:
            print() # ensure last print is a newline

    def reset(self, force = False):
        """Resets the instance.

        Args:
            force: A boolean indicating to force the reset even if in
                persitent mode.
        """

        self.buf = None
        if force or not self.keep:
            self.count  = 0
            self.ins    = None
            self.loops  = {}
            self.sr     = 0
            self.pc     = 0
            self.mem    = [0] * (1 if not self.strict else self.memmax)
            # reduce len() calls
            self.inslen = 0
            self.memlen = self.memmax if self.strict else len(self.mem)

    def script(self, paths):
        """Return the first BrainFuck program from the given scripts paths.

        Args:
            paths: A list of file paths pointing to text files
                containing BrainFuck code.

        Returns:
            None if no program is found, else the program.
        """

        prog = None
        if paths and len(paths) > 0:
            prog = ""
            if not self.keep: paths = paths[:1]
            for p in paths:
                with open(p, "r") as f:
                    prog = prog + "".join(
                        [
                            l.strip().split(self.lang.get("comments").get("left"))[0]
                            for l in f.readlines()
                            if not l.startswith(self.lang.get("comments").get("left"))
                        ]
                    )
            self.inslen = len(prog)
        return prog

    def shell(self):
        """Retrieve a piece of BrainFuck program from an interactive shell.

        Returns:
            None if no program is given, else the program.
        """

        prog = None
        if self.inp(isInstruction=True):
            prog = (self.ins if self.ins else "") + (self.buf if self.buf else "")
            self.inslen += len(self.buf if self.buf else "")
            self.buf = None
        return prog

    def execute(self, shell=False):
        """Execute the BrainFuck program.

        Args:
            shell: A boolean indicating if the execution is done
                through a shell.
        """

        while(True):
            # self.dbg will always return None, but is better used
            # between the instruction and jump.
            if self.translate() or self.dbg() or not self.jump(): break
        if not shell: self.dbg(True)
        self.reset()

    def translate(self):
        """Execute the current BrainFuck instruction.

        Returns:
            non-True if the program can continue, True otherwise.
        """

        action = self.action.get(self.instruction())
        if action: return action()

    def instruction(self, pc=None):
        """Give the current BrainFuck instruction.

        Args:
            pc: The instruction index in the program.

        Returns:
            The current BrainFuck instruction symbol.
        """

        pc = pc if pc else self.pc
        if pc < self.inslen: return self.ins[pc]

    def jump(self, to=None):
        """Go to the next valid instruction.

        Args:
            to: The position to jump to as an integer between
              [0, program len). Default to the current position +1.

        Returns:
            False if the end of the program is reached, else True.
        """

        self.pc = to if to is not None else self.pc + 1
        return self.pc < self.inslen

    def dbg(self, report=False):
        """Print debugging informations.

        Args:
            report: A boolean making the function print a report on
                the BrainFuck program.
        """

        self.count += 1
        if self.debug:
            if report:
                print(
                    "Done with: {} instructions, {} steps, {} bytes".format(
                        self.inslen, self.count, self.memlen
                    ),
                    file = sys.stderr
                )
            elif self.instruction():
                print(
                    "PC: {:3} ('{}'), PTR: *({:2}) = {:3}".format(
                        self.pc, self.instruction(), self.sr, self.value()
                    ),
                    file = sys.stderr
                )

    def value(self, value = None):
        """Get or set the current memory value.

        If value is None, the function acts as a getter, and a setter
        if value is not None.

        Args:
            value: The value to set in memory.

        Returns:
            If value is None, returns the current byte value; else
            returns None.
        """

        if value is not None: self.mem[self.sr] = value
        else: return self.mem[self.sr]

    def loop(self):
        """Handle loops."""

        if self.loops.get(self.pc) is None: self.registerLoop()

        if not (bool(self.value()) ^ (self.instruction() == self.lang.get("loops").get("right"))):
            self.jump(self.loops.get(self.pc))

    def registerLoop(self):
        """Register loops start and end positions.

        Raises:
            BrainFuckingGoneError: if a dangling loop character is
              detected.
        """

        isEnd = self.instruction() == self.lang.get("loops").get("right")
        char  = self.lang.get("loops").get("left" if isEnd else "right")
        start = self.pc+1
        end   = 0 if isEnd else self.inslen
        step  = -1 if isEnd else 1

        sibling = None
        count = 0
        for i in range(start, end, step):
            if self.instruction(i) == self.instruction():
                count += 1
            elif self.instruction(i) == char:
                if count > 0: count -= 1
                else:
                    sibling = i
                    break

        if sibling is None:
            raise BrainFuckingGoneError("Syntax error: dangling '{}' at position {}.".format(self.instruction(), self.pc))
        self.loops[self.pc] = sibling
        self.loops[sibling] = self.pc

    def ptr(self):
        """Increment or decrement the pointer value."""

        if   self.instruction() == self.lang.get("ptrs").get("left"):  self.sr -= 1
        elif self.instruction() == self.lang.get("ptrs").get("right"): self.sr += 1
        self.segflt()

    def segflt(self):
        """Check for segfaults errors and raise them if any."""

        if self.sr >= self.memlen:
            if self.strict:
                raise BrainFuckingGoneError(
                    self.errmsg.format(
                        "Segfault", self.pc, self.instruction(),
                        "data pointer value above the maximum (strict mode: on)"
                    ))
            else:
                self.mem.append(0)
                self.memlen += 1
        elif self.sr < 0:
            raise BrainFuckingGoneError(
                self.errmsg.format(
                    "Segfault", self.pc, self.instruction(),
                    "negative data pointer value"
                ))

    def byte(self):
        """Increment or decrement the byte value with over/underflow."""

        newValue = self.value()
        if   self.instruction() == self.lang.get("bytes").get("left"):  newValue -= 1
        elif self.instruction() == self.lang.get("bytes").get("right"): newValue += 1

        # Over/underflow.
        if   newValue < self.minmax[0]: newValue = self.minmax[1] - abs(newValue) + 1
        elif newValue > self.minmax[1]: newValue = self.minmax[0] + abs(newValue) - 1

        self.value(newValue)

    def inp(self, prompt=" > ", isInstruction=False):
        """Ask for input.

        The input value is stored in the self.buf variable.

        Args:
            prompt: The prompt to show to the user.

        Returns:
            True if a value has been entered, False if EOF.
        """

        try:
            if isInstruction:
                self.buf = input(prompt)
                return True
            elif self.remain is not None:
                self.buf = self.remain[0]
                self.remain = self.remain[1:]
                if len(self.remain) == 0:
                    self.remain = None
                return True
            else:
                self.remain = input()
                return self.inp()
        except EOFError:
            return False

    def inout(self):
        """Handle IO.

        Returns:
            True if the program must stop (EOF from the user), None otherwise.
        """

        if self.instruction() == self.lang.get("ios").get("right"):
            output = chr(self.value())
            if self.debug and self.stdout is not None:
                self.stdout = self.stdout + output
            else:
                print(output, end="" if not self.debug else "\n")
        elif self.instruction() == self.lang.get("ios").get("left"):
            if not self.inp("\n?> "): return True
            self.value(ord(self.buf))
            self.buf = None

    def ignoreUntil(self, until=None):
        """Ignore a region of instructions

        Args:
            until: The ending limit character of the region to ignore
                (default to the right side of comments)
        """

        until = until if until is not None else self.lang.get("comments").get("right")
        while(self.instruction() != until and self.jump()): pass

if __name__ == "__main__":
    bfg = BrainFuckingGone()
    epilog = "License {} - {}".format(__license__, __copyright__)
    parser = argparse.ArgumentParser(
        prog = "bfg",
        description = "BrainFucking Gone v{} - A simple BrainFuck interpreter.".format(__version__),
        epilog=epilog
    )
    parser.add_argument(
        "-v", "--version", action="store_true",
        help="display the version number and exit"
    )
    parser.add_argument(
        "-w", "--license", action="store_true",
        help="display the license text and exit"
    )
    parser.add_argument(
        "-p", "--persistent", action="store_true",
        help="make the memory persist between scripts execution (always True in the shell)"
    )
    parser.add_argument(
        "-d", "--debug", action="store_true",
        help="print debugging info at each step (always True in the shell)"
    )
    parser.add_argument(
        "-s", "--strict",
        action="store_true",
        help="use 'strict' mode: memory limited to {} bytes".format(bfg.memmax, bfg.minmax)
    )
    parser.add_argument(
        "-f", "--file", action="append",
        help="Path of a program stored in a text file"
    )
    args = parser.parse_args()

    if args.version or args.license:
        print(__version__ if args.version else epilog)
        exit(0)

    bfg.run(args.file, args.persistent, args.debug, args.strict)
