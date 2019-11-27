"""Module for managing Hyrise databases.

Includes the HyriseInterface, which uses an InstanceManager and a LoadGenerator.
These are responsible for submitting the requested jobs to a Queue.
"""

import json
import time

import redis
import zmq

import settings as s
from apscheduler.schedulers.background import BackgroundScheduler

from .InstanceManager import InstanceManager
from .LoadGenerator import LoadGenerator


class HyriseInterface(object):
    """An interface for concrete Hyrise databases."""

    def __init__(self):
        """Initialize a HyriseInterface with an InstanceManager and a LoadGenerator."""
        self.instanceManager = InstanceManager()
        self.loadGenerator = LoadGenerator()
        self.scheduler = BackgroundScheduler()
        self.scheduler.add_job(
            func=self.update_throughput, trigger="interval", seconds=1,
        )
        self.scheduler.start()
        self.throughput_counter = "0"
        self.r = redis.Redis()
        self.init_redis()
        self.instanceManager.get_storage_data()
        self.databases = dict()

    def init_redis(self):
        """Set basic values in redis db."""
        self.r.set("throughput", 0)
        self.r.set("throughput_counter", 0)
        self.r.set("start_time_intervall", time.time())

    def update_throughput(self):
        """Update throughput."""
        self.throughput_counter = self.r.get("throughput_counter").decode("utf-8")
        print(self.throughput_counter)
        self.r.set("throughput_counter", 0)

    def start(self):
        """Start with default values."""
        context = zmq.Context()
        socket = context.socket(zmq.REP)
        socket.bind(f"tcp://{s.HYRISE_INTERFACE_HOST}:{s.HYRISE_INTERFACE_PORT}")
        print("Hyrise Interface running. Press Ctrl+C to stop.")

        while True:
            message = socket.recv()
            data = json.loads(message)
            response = ""
            if data["Content-Type"] == "query":
                self.execute_raw_query(data["Content"])
                response = "OK"
            elif data["Content-Type"] == "workload":
                self.execute_raw_workload(data["Content"])
                response = "OK"
            elif data["Content-Type"] == "storage_data":
                response = self.r.get("storage_data").decode("utf-8")
            elif data["Content-Type"] == "throughput":
                response = json.dumps({"throughput": self.throughput_counter})
            elif data["Content-Type"] == "runtime_information":
                response = "[NOT IMPLEMENTED YETWorkload]"
                pass
            else:
                response = "[Error]"

            socket.send_string(response)

    def add_hyrise_instance(self, id, host, port, user, password, name=""):
        """Add hyrise instance."""
        if id not in self.databases.keys():
            self.databases[id] = {
                "name": name,
                "host": host,
                "port": port,
                "user": user,
                "password": password,
            }
            return id
        return False

    def pop_hyrise_instance(self, id):
        """Remove hyrise instance."""
        if id in self.databases.keys():
            del self.databases[id]
            return id
        return False

    def get_storage_data(self):
        """Get storage data from InstanceManager."""
        return self.instanceManager.get_storage_data()

    def execute_raw_query(self, query):
        """Execute a SQL query."""
        return self.loadGenerator.execute_raw_query(query)

    def execute_raw_workload(self, workload):
        """Execute a list of SQL queries forming a workload."""
        return self.loadGenerator.execute_raw_workload(workload)


def main():
    """Run a HyriseInterface."""
    HyriseInterface().start()


if __name__ == "__main__":
    main()
