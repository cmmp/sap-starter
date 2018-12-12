#!/usr/bin/env python

import subprocess as sub
import logging
import time
import argparse
import json


class ProcessGroup:
    def __init__(self, server_nr, max_retries=4):
        self.server_nr = server_nr
        self.procs = self.update_procs_status()
        self.max_retries = max_retries

    def backoff_generator(self,):
        yield 1
        n = 1
        while True:
            yield 5 * n
            n += 1

    def start_process(self,):
        cmd = [
            "/usr/sap/hostctrl/exe/sapcontrol",
            "-nr",
            str(self.server_nr),
            "-function",
            "RestartSystem",
        ]

        backgen = self.backoff_generator()
        retries = 1
        started = False

        while not started and retries <= self.max_retries:
            logging.info(
                "Starting process group {}. This is retry number {} of {}".format(
                    self.server_nr, retries, self.max_retries
                )
            )
            p = sub.Popen(cmd, stdout=sub.PIPE)
            p.communicate()
            p.wait()

            sleepTime = next(backgen)
            logging.info("Going to sleep for {} minute(s)...".format(sleepTime))
            time.sleep(sleepTime * 60)
            self.procs = self.update_procs_status()

            if self.everything_green():
                logging.info(
                    "Successfull start of process group {}".format(self.server_nr)
                )
                started = True
                break

            retries += 1

        if not started:
            logging.info(
                "Failed to start process group {} after {} retries.".format(
                    self.server_nr, self.max_retries
                )
            )

        return started

    def update_procs_status(self,):
        cmd = [
            "/usr/sap/hostctrl/exe/sapcontrol",
            "-nr",
            str(self.server_nr),
            "-function",
            "GetProcessList",
            "-format",
            "script",
        ]

        proc = sub.Popen(cmd, stdout=sub.PIPE)
        (output, _) = proc.communicate()
        proc.wait()

        lines = output.split("\n")[4:-1]  # remove header and trailing data

        return OutputProcessor(self.server_nr, lines).process_output()

    def get_procs(self):
        return self.procs

    def filter_by_status(self, status="GREEN"):
        return len(filter(lambda x: x["status"] == status, self.procs))

    def everything_green(self):
        return self.count_greens() == self.count_total()

    def count_total(self):
        return len(self.procs)

    def count_greens(self):
        return self.filter_by_status()

    def count_grays(self):
        return self.filter_by_status("GRAY")

    def count_yellows(self):
        return self.filter_by_status("YELLOW")

    def count_reds(self):
        return self.filter_by_status("RED")


class OutputProcessor:
    def __init__(self, server_nr, lines):
        self.server_nr = server_nr
        self.lines = lines
        self.nblocks = len(lines) / 7

    def get_parsed_line(self, block, pos):
        tkns = self.lines[block * 7 + pos].split()
        return tkns[2] if len(tkns) >= 3 else ""

    def get_proc_name(self, block):
        return self.get_parsed_line(block, 0)

    def get_proc_desc(self, block):
        return self.get_parsed_line(block, 1)

    def get_proc_status(self, block):
        return self.get_parsed_line(block, 2)

    def get_proc_txt_status(self, block):
        return self.get_parsed_line(block, 3)

    def get_proc_start_time(self, block):
        return self.get_parsed_line(block, 4)

    def get_proc_elapsed_time(self, block):
        return self.get_parsed_line(block, 5)

    def get_proc_pid(self, block):
        return self.get_parsed_line(block, 6)

    def process_output(self,):
        procs = []
        for i in range(self.nblocks):
            procs.append(
                {
                    "name": self.get_proc_name(i),
                    "desc": self.get_proc_desc(i),
                    "status": self.get_proc_status(i),
                    "txt_status": self.get_proc_txt_status(i),
                    "start_time": self.get_proc_start_time(i),
                    "elapsed_time": self.get_proc_elapsed_time(i),
                    "pid": self.get_proc_pid(i),
                }
            )
        return procs


def start_sequence(sequence):
    all_ok = True
    for seq_nr in sequence:
        pg = ProcessGroup(seq_nr)
        ret = pg.start_process()
        if not ret:
            logging.info(
                "Could not start sequence because process group {} failed. Giving up.".format(
                    seq_nr
                )
            )
            all_ok = False
            break
    logging.info("Successfully started sequence") if all_ok else logging.info(
        "Startup sequence failed."
    )


def show_status(status):
    pg = ProcessGroup(status)
    print(json.dumps(pg.get_procs(), indent=2))


if __name__ == "__main__":
    logging.basicConfig(
        format="%(asctime)s %(levelname)s: %(message)s",
        datefmt="%m/%d/%Y %I:%M:%S %p",
        level=logging.INFO,
    )

    parser = argparse.ArgumentParser(description="Start SAP sequence program")
    parser.add_argument(
        "--start",
        type=int,
        nargs="+",
        help="The sequence of process groups to be started, in order.",
    )
    parser.add_argument(
        "--status",
        action="store",
        type=int,
        nargs=1,
        help="The process group number to show the status.",
        required=False,
    )

    args = parser.parse_args()
    if args.start is not None:
        start_sequence(args.start)
    elif args.status is not None:
        show_status(args.status[0])
    else:
        parser.print_help()
