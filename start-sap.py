#!/usr/bin/env python

import subprocess as sub
import pdb


class ProcessGroup:
    def __init__(self, server_nr):
        self.server_nr = server_nr
        self.procs = self.update_procs_status()

    def start_process(self,):
        cmd = [
            "/usr/sap/hostctrl/exe/sapcontrol",
            "-nr",
            str(self.server_nr),
            "-function",
            "RestartSystem",
            "-format",
            "script",
        ]
        proc = sub.Popen(cmd, stdout=sub.PIPE)
        proc.communicate()
        proc.wait()

        started = False

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


pg = ProcessGroup(0)
pdb.set_trace()
