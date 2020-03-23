"""Module for monitoring a database interface.

Includes routes for throughput, storage_data, and runtime_information.
If run as a module, a flask server application will be started.
"""

from json import loads
from time import time_ns
from typing import Any, Dict, List, Union

from flask import Flask
from flask_cors import CORS
from flask_restx import Api, Resource, fields
from influxdb import InfluxDBClient
from jsonschema import ValidationError, validate
from zmq import REQ, Context, Socket

from hyrisecockpit.message import get_databases_response_schema, response_schema
from hyrisecockpit.plugins import available_plugins
from hyrisecockpit.request import Header, Request
from hyrisecockpit.response import Response, get_error_response, get_response
from hyrisecockpit.settings import (
    DB_MANAGER_HOST,
    DB_MANAGER_PORT,
    GENERATOR_HOST,
    GENERATOR_PORT,
    STORAGE_HOST,
    STORAGE_PASSWORD,
    STORAGE_PORT,
    STORAGE_USER,
)

context = Context(io_threads=1)

db_manager_socket = context.socket(REQ)
db_manager_socket.connect(f"tcp://{DB_MANAGER_HOST}:{DB_MANAGER_PORT}")

generator_socket = context.socket(REQ)
generator_socket.connect(f"tcp://{GENERATOR_HOST}:{GENERATOR_PORT}")


storage_connection = InfluxDBClient(
    STORAGE_HOST, STORAGE_PORT, STORAGE_USER, STORAGE_PASSWORD
)

app = Flask(__name__)
cors = CORS(app)
api = Api(
    app,
    title="Hyrise Cockpit",
    description="Monitor and control multiple databases at once.",
    validate=True,
)

monitor = api.namespace(
    "monitor", description="Get synchronous data from multiple databases at once."
)

control = api.namespace("control", description="Control multiple databases at once.")

model_database = monitor.model(
    "Database",
    {
        "id": fields.String(
            title="Database ID",
            description="Used to identify a database.",
            required=True,
            example="hyrise-1",
        )
    },
)

model_throughput = monitor.clone(
    "Throughput",
    model_database,
    {
        "throughput": fields.Integer(
            title="Throughput",
            description="Query throughput of a given time interval.",
            required=True,
            example=7381,
        )
    },
)

model_detailed_throughput = monitor.clone(
    "Detailed Throughput",
    model_database,
    {
        "detailed_throughput": fields.List(
            fields.Nested(
                monitor.model(
                    "Throughput per query",
                    {
                        "workload_type": fields.String(
                            title="workload_type",
                            description="Type of the executed query.",
                            required=True,
                            example="tpch_0.1",
                        ),
                        "query_number": fields.Integer(
                            title="query_number",
                            description="Number of the executed query",
                            required=True,
                            example=5,
                        ),
                        "throughput": fields.Integer(
                            title="throughput",
                            description="Number of successfully executed queries in given time interval.",
                            required=True,
                            example=55,
                        ),
                    },
                )
            ),
            required=True,
        )
    },
)

model_query_information = monitor.clone(
    "Detailed Throughput and Latency",
    model_database,
    {
        "detailed_query_information": fields.List(
            fields.Nested(
                monitor.model(
                    "Throughput and latency per query",
                    {
                        "workload_type": fields.String(
                            title="workload_type",
                            description="Type of the executed query.",
                            required=True,
                            example="tpch_0.1",
                        ),
                        "query_number": fields.Integer(
                            title="query_number",
                            description="Number of the executed query",
                            required=True,
                            example=5,
                        ),
                        "throughput": fields.Integer(
                            title="throughput",
                            description="Number of successfully executed queries in given time interval.",
                            required=True,
                            example=55,
                        ),
                        "latency": fields.Float(
                            title="Latency",
                            description="Average query latency (ns) of a given time interval.",
                            required=True,
                            example=923.263,
                        ),
                    },
                )
            ),
            required=True,
        )
    },
)

model_latency = monitor.clone(
    "Latency",
    model_database,
    {
        "latency": fields.Float(
            title="Latency",
            description="Average query latency (ns) of a given time interval.",
            required=True,
            example=923.263,
        )
    },
)

model_detailed_latency = monitor.clone(
    "Detailed Latency",
    model_database,
    {
        "detailed_latency": fields.List(
            fields.Nested(
                monitor.model(
                    "Latency per query",
                    {
                        "workload_type": fields.String(
                            title="workload_type",
                            description="Type of the executed query.",
                            required=True,
                            example="tpch_0.1",
                        ),
                        "query_number": fields.Integer(
                            title="query_number",
                            description="Number of the executed query",
                            required=True,
                            example=5,
                        ),
                        "latency": fields.Integer(
                            title="latency",
                            description="Time passed between starting to execute a query and receiving the result.",
                            required=True,
                            example=98634929882,
                        ),
                    },
                )
            ),
            required=True,
        )
    },
)

model_queue_length = monitor.clone(
    "Queue length",
    model_database,
    {
        "queue_length": fields.Integer(
            title="Queue length",
            description="Query queue length of a database at a given point in time.",
            required=True,
            example=18623,
        )
    },
)

model_workload_composition = monitor.model(
    "Workload composition",
    {
        "SELECT": fields.Integer(
            title="SELECT queries",
            description="Number of SELECT queries of a given time interval.",
            required=True,
            example=241,
        ),
        "INSERT": fields.Integer(
            title="INSERT queries",
            description="Number of INSERT queries of a given time interval.",
            required=True,
            example=67,
        ),
        "UPDATE": fields.Integer(
            title="UPDATE queries",
            description="Number of UPDATE queries of a given time interval.",
            required=True,
            example=573,
        ),
        "DELETE": fields.Integer(
            title="DELETE queries",
            description="Number of DELETE queries of a given time interval.",
            required=True,
            example=14,
        ),
    },
)

model_krueger_data = monitor.clone(
    "Krüger data",
    model_database,
    {
        "executed": fields.Nested(
            model_workload_composition,
            title="Executed queries",
            description="The composition of queries successfully exectued of a given time interval.",
            required=True,
        ),
        "generated": fields.Nested(
            model_workload_composition,
            title="Generated queries",
            description="The composition of queries generated of a given time interval.",
            required=True,
        ),
    },
)

model_database_status = monitor.clone(
    "Database status",
    model_database,
    {
        "database_blocked_status": fields.Boolean(
            title="Database blocked status",
            description="Database blocked status of databases.",
            required=True,
            example=True,
        ),
        "worker_pool_status": fields.String(
            title="Worker pool status",
            description="Status of the worker pools of the databases.",
            required=True,
            example="running",
        ),
        "loaded_benchmarks": fields.List(
            fields.String(
                title="Benchmark",
                description="Benchmark dataset that is completely loaded.",
                required=True,
                example="tpch_1",
            ),
        ),
        "loaded_tables": fields.List(
            fields.Nested(
                monitor.model(
                    "Loaded tables",
                    {
                        "table_name": fields.String(
                            title="Table name",
                            description="Name of loaded table",
                            required=True,
                            example="customer",
                        ),
                        "benchmark": fields.String(
                            title="Benchmark",
                            description="Name of the benchmark",
                            required=True,
                            example="tpch_0.1",
                        ),
                    },
                )
            ),
            required=True,
        ),
    },
)

model_data = control.model(
    "Data",
    {
        "folder_name": fields.String(
            title="Folder name",
            description="Name of the folder containing the pregenerated tables.",
            required=True,
            example="tpch_0.1",
        )
    },
)

model_storage = control.model(
    "storage",
    {
        fields.String(
            title="Database ID",
            description="Used to identify a database.",
            required=True,
            example="hyrise-1",
        ): {
            fields.String(
                title="Tablename",
                description="Name of the table.",
                required=True,
                example="aka_name",
            ): {
                "size": fields.Integer(
                    title="Size",
                    description="Estimated size of the table given in bytes.",
                    required=True,
                    example="2931788734",
                ),
                "number_columns": fields.Integer(
                    title="Number of columns",
                    description="Number of columns of the table.",
                    required=True,
                    example="112",
                ),
                "data": {
                    "column_name": {
                        "size": fields.Integer(
                            title="Size",
                            description="Estimated size of the column given in bytes.",
                            required=True,
                            example="8593371",
                        ),
                        "encoding": fields.String(
                            title="Encoding",
                            description="Encodings of the column.",
                            required=True,
                            example="Dictionary",
                        ),
                        "data_type": fields.String(
                            title="Datatype",
                            description="Datatype of the column.",
                            required=True,
                            example="String",
                        ),
                    }
                },
            }
        }
    },
)

model_control_database = control.model(
    "Database",
    {
        "id": fields.String(
            title="Database ID",
            description="Used to identify a database.",
            required=True,
            example="hyrise-1",
        )
    },
)

model_get_database = control.clone(
    "Get Database",
    model_control_database,
    {
        "host": fields.String(
            title="Host",
            description="Host to log in to.",
            required=True,
            example="vm.example.com",
        ),
        "port": fields.String(
            title="Port",
            description="Port of the host to log in to.",
            required=True,
            example="1234",
        ),
        "number_workers": fields.Integer(
            title="Number of initial database worker processes.",
            description="",
            required=True,
            example=8,
        ),
        "dbname": fields.String(
            title="",
            description="Name of the database to log in to.",
            required=True,
            example="mydb",
        ),
    },
)

model_add_database = control.clone(
    "Add Database",
    model_get_database,
    {
        "user": fields.String(
            title="Username",
            description="Username used to log in.",
            required=True,
            example="user123",
        ),
        "password": fields.String(
            title="Password",
            description="Password used to log in.",
            required=True,
            example="password123",
        ),
    },
)

modelhelper_plugin = fields.String(
    title="Plugin name",
    description="Used to identify a plugin.",
    required=True,
    example="Clustering",
)

model_plugin_log = control.clone(
    "Plugin Log",
    model_database,
    {
        "plugin_log": fields.List(
            fields.Nested(
                control.model(
                    "Plugin Log Entry",
                    {
                        "timestamp": fields.Integer(
                            title="Timestamp",
                            description="Timestamp in nanoseconds.",
                            required=True,
                            example=1583847966784,
                        ),
                        "reporter": fields.String(
                            title="Reporter",
                            description="Plugin reporting to the log.",
                            required=True,
                            example="CompressionPlugin",
                        ),
                        "message": fields.String(
                            title="Message",
                            description="Message logged.",
                            required=True,
                            example="No optimization possible with given parameters!",
                        ),
                    },
                )
            ),
            required=True,
        )
    },
)

model_get_all_plugins = control.model(
    "Available Plugins", {"plugins": fields.List(modelhelper_plugin, required=True,)},
)

model_get_activated_plugins = control.clone(
    "Activated Plugins",
    model_database,
    {"plugins": fields.List(modelhelper_plugin, required=True,)},
)

model_activate_plugin = control.clone(
    "Activate Plugin", model_database, {"plugin": modelhelper_plugin},
)

model_deactivate_plugin = control.clone(
    "Deactivate Plugin", model_database, {"plugin": modelhelper_plugin},
)

model_plugin_setting = control.clone(
    "Set Plugin Setting",
    model_database,
    {
        "name": fields.String(
            title="Setting name",
            description="Name of the setting that shall be set.",
            required=True,
            example="CompressionPlugin_MemoryBudget",
        ),
        "value": fields.String(
            title="Setting value",
            description="Value the setting should have.",
            required=True,
            example="5000",
        ),
    },
)

model_get_plugin_setting = control.clone(
    "Get Plugin Setting",
    model_plugin_setting,
    {
        "description": fields.String(
            title="Setting description",
            description="Description of the plugin setting.",
            required=True,
            example="The memory budget to target for the Compression...",
        ),
    },
)


def _send_message(socket: Socket, message: Request) -> Response:
    """Send an IPC message with data to a database interface, return the repsonse."""
    socket.send_json(message)
    response: Response = socket.recv_json()
    validate(instance=response, schema=response_schema)
    return response


def _active_databases() -> List[str]:
    """Get a list of active databases."""
    response: Response = _send_message(
        db_manager_socket, {"header": {"message": "get databases"}, "body": {}}
    )
    validate(instance=response["body"], schema=get_databases_response_schema)
    return [database["id"] for database in response["body"]["databases"]]


@monitor.route("/throughput")
class Throughput(Resource):
    """Throughput information of all databases."""

    @monitor.doc(model=[model_throughput])
    def get(self) -> Union[int, Response]:
        """Return throughput information from the stored queries."""
        currentts = time_ns()
        startts = currentts - 2_000_000_000
        endts = currentts - 1_000_000_000

        throughput: Dict[str, int] = {}
        try:
            active_databases = _active_databases()
        except ValidationError:
            return 500
        for database in active_databases:
            result = storage_connection.query(
                'SELECT COUNT("latency") FROM successful_queries WHERE time > $startts AND time <= $endts;',
                database=database,
                bind_params={"startts": startts, "endts": endts},
            )
            throughput_value = list(result["successful_queries", None])
            if len(throughput_value) > 0:
                throughput[database] = list(result["successful_queries", None])[0][
                    "count"
                ]
            else:
                throughput[database] = 0
        response = get_response(200)
        response["body"]["throughput"] = throughput
        return response


@monitor.route("/detailed_throughput")
class DetailedThroughput(Resource):
    """Detailed throughput information of all databases."""

    @monitor.doc(model=[model_detailed_throughput])
    def get(self) -> Union[int, List[Dict[str, Any]]]:
        """Return detailed throughput information from the stored queries."""
        currentts = time_ns()
        startts = currentts - 2_000_000_000
        endts = currentts - 1_000_000_000
        try:
            active_databases = _active_databases()
        except ValidationError:
            return 500
        response: List[Dict] = []
        for database in active_databases:
            result = storage_connection.query(
                'SELECT COUNT("latency") FROM successful_queries WHERE time > $startts AND time <= $endts GROUP BY benchmark, query_no;',
                database=database,
                bind_params={"startts": startts, "endts": endts},
            )
            throughput: List[Dict[str, int]] = [
                {
                    "benchmark": tags["benchmark"],
                    "query_number": tags["query_no"],
                    "throughput": list(result[table, tags])[0]["count"],
                }
                for table, tags in list(result.keys())
            ]
            response.append({"id": database, "detailed_throughput": throughput})
        return response


@monitor.route("/detailed_latency")
class DetailedLatency(Resource):
    """Detailed throughput information of all databases."""

    @monitor.doc(model=[model_detailed_latency])
    def get(self) -> Union[int, List[Dict[str, Any]]]:
        """Return detailed throughput information from the stored queries."""
        currentts = time_ns()
        startts = currentts - 2_000_000_000
        endts = currentts - 1_000_000_000
        try:
            active_databases = _active_databases()
        except ValidationError:
            return 500
        response: List[Dict] = []
        for database in active_databases:
            result = storage_connection.query(
                'SELECT MEAN("latency") as "latency" FROM successful_queries WHERE time > $startts AND time <= $endts GROUP BY benchmark, query_no;',
                database=database,
                bind_params={"startts": startts, "endts": endts},
            )
            latency: List[Dict[str, int]] = [
                {
                    "benchmark": tags["benchmark"],
                    "query_number": tags["query_no"],
                    "latency": list(result[table, tags])[0]["latency"],
                }
                for table, tags in list(result.keys())
            ]
            response.append({"id": database, "detailed_latency": latency})
        return response


@monitor.route("/latency")
class Latency(Resource):
    """Latency information of all databases."""

    @monitor.doc(model=[model_latency])
    def get(self) -> Union[int, Response]:
        """Return latency information from the stored queries."""
        currentts = time_ns()
        startts = currentts - 2_000_000_000
        endts = currentts - 1_000_000_000
        latency: Dict[str, float] = {}
        try:
            active_databases = _active_databases()
        except ValidationError:
            return 500
        for database in active_databases:
            result = storage_connection.query(
                'SELECT MEAN("latency") as "latency" FROM successful_queries WHERE time > $startts AND time <= $endts;',
                database=database,
                bind_params={"startts": startts, "endts": endts},
            )
            latency_value = list(result["successful_queries", None])
            if len(latency_value) > 0:
                latency[database] = list(result["successful_queries", None])[0][
                    "latency"
                ]
            else:
                latency[database] = 0
        response = get_response(200)
        response["body"]["latency"] = latency
        return response


@monitor.route("/detailed_query_information")
class DetailedQueryInformation(Resource):
    """Detailed throughput and latency information of all databases."""

    @monitor.doc(model=[model_query_information])
    def get(self) -> Union[int, List[Dict[str, Any]]]:
        """Return detailed throughput and latency information from the stored queries."""
        currentts = time_ns()
        startts = currentts - 2_000_000_000
        endts = currentts - 1_000_000_000
        try:
            active_databases = _active_databases()
        except ValidationError:
            return 500
        response: List[Dict] = []
        for database in active_databases:
            result = storage_connection.query(
                'SELECT COUNT("latency") as "throughput", MEAN("latency") as "latency" FROM successful_queries WHERE time > $startts AND time <= $endts GROUP BY benchmark, query_no;',
                database=database,
                bind_params={"startts": startts, "endts": endts},
            )
            query_information: List[Dict[str, int]] = [
                {
                    "benchmark": tags["benchmark"],
                    "query_number": tags["query_no"],
                    "throughput": list(result[table, tags])[0]["throughput"],
                    "latency": list(result[table, tags])[0]["latency"],
                }
                for table, tags in list(result.keys())
            ]
            response.append({"id": database, "query_information": query_information})

        return response


@monitor.route("/queue_length")
class QueueLength(Resource):
    """Queue length information of all databases."""

    @monitor.doc(model=[model_queue_length])
    def get(self) -> Response:
        """Return queue length information from database manager."""
        return _send_message(
            db_manager_socket, {"header": {"message": "queue length"}, "body": {}}
        )


@monitor.route("/failed_tasks")
class FailedTasks(Resource):
    """Failed tasks information of all databases."""

    def get(self) -> List[Dict[str, Union[str, List]]]:
        """Return queue length information from database manager."""
        return [
            {
                "id": database,
                "failed_queries": list(
                    storage_connection.query(
                        "SELECT * FROM failed_queries LIMIT 100;", database=database,
                    )["failed_queries", None]
                ),
            }
            for database in _active_databases()
        ]


@monitor.route("/system")
class System(Resource):
    """System data information of all databases."""

    def get(self) -> Union[int, Response]:
        """Return cpu and memory information for every database and the number of thread it is using from database manager."""
        system: Dict[str, Dict] = {}
        try:
            active_databases = _active_databases()
        except ValidationError:
            return 500
        for database in active_databases:
            result = storage_connection.query(
                'SELECT LAST("cpu"), * FROM system_data', database=database,
            )
            system_value = list(result["system_data", None])
            if len(system_value) > 0:
                system[database] = {
                    "cpu": loads(system_value[0]["cpu"]),
                    "memory": loads(system_value[0]["memory"]),
                    "database_threads": loads(system_value[0]["database_threads"]),
                }
            else:
                system[database] = {}
        response = get_response(200)
        response["body"]["system_data"] = system
        return response


@monitor.route("/chunks")
class Chunks(Resource):
    """Chunks data information of all databases."""

    def get(self) -> Union[int, Response]:
        """Return chunks data information for every database."""
        chunks: Dict[str, Dict] = {}
        try:
            active_databases = _active_databases()
        except ValidationError:
            return 500
        for database in active_databases:
            result = storage_connection.query(
                'SELECT LAST("chunks_data_meta_information") FROM chunks_data',
                database=database,
            )
            chunks_value = list(result["chunks_data", None])
            if len(chunks_value) > 0:
                chunks[database] = loads(chunks_value[0]["last"])
            else:
                chunks[database] = {}
        response = get_response(200)
        response["body"]["chunks_data"] = chunks
        return response


@monitor.route("/storage")
class Storage(Resource):
    """Storage information of all databases."""

    # @control.doc(body=[model_storage]) # noqa
    def get(self) -> Union[int, Response]:
        """Return storage metadata from database manager."""
        storage: Dict[str, Dict] = {}
        try:
            active_databases = _active_databases()
        except ValidationError:
            return 500
        for database in active_databases:
            result = storage_connection.query(
                'SELECT LAST("storage_meta_information") FROM storage',
                database=database,
            )
            storage_value = list(result["storage", None])
            if len(storage_value) > 0:
                storage[database] = loads(storage_value[0]["last"])
            else:
                storage[database] = {}
        response = get_response(200)
        response["body"]["storage"] = storage
        return response


@monitor.route("/krueger_data", methods=["GET"])
class KruegerData(Resource):
    """Krügergraph data for all workloads."""

    @monitor.doc(model=[model_krueger_data])
    def get(self) -> Union[int, List[Dict[str, Dict[str, Dict]]]]:
        """Provide mock data for a Krügergraph."""
        krueger_data: List[Dict] = []
        try:
            active_databases = _active_databases()
        except ValidationError:
            return 500
        for database in active_databases:
            result = storage_connection.query(
                'SELECT LAST("executed"), * FROM krueger_data', database=database,
            )
            krueger_data_value = list(result["krueger_data", None])
            if len(krueger_data_value) > 0:
                krueger_data.append(
                    {
                        "id": database,
                        "executed": loads(krueger_data_value[0]["executed"]),
                        "generated": loads(krueger_data_value[0]["generated"]),
                    }
                )
            else:
                krueger_data.append({"id": database, "executed": {}, "generated": {}})
        return krueger_data


@monitor.route("/status", methods=["GET"])
class ProcessTableStatus(Resource):
    """Database blocked status information of all databases."""

    @monitor.doc(model=[model_database_status])
    def get(self) -> List[Dict]:
        """Return status of databases."""
        return _send_message(
            db_manager_socket, Request(header=Header(message="status"), body={}),
        )["body"]["status"]


@control.route("/database", methods=["GET", "POST", "DELETE"])
class Database(Resource):
    """Manages databases."""

    @control.doc(model=[model_get_database])
    def get(self) -> Response:
        """Get all databases."""
        message = Request(header=Header(message="get databases"), body={})
        response = _send_message(db_manager_socket, message)
        return response["body"]["databases"]

    @control.doc(body=model_add_database)
    def post(self) -> Response:
        """Add a database."""
        message = Request(
            header=Header(message="add database"),
            body={
                "number_workers": control.payload["number_workers"],
                "id": control.payload["id"],
                "user": control.payload["user"],
                "password": control.payload["password"],
                "host": control.payload["host"],
                "port": control.payload["port"],
                "dbname": control.payload["dbname"],
            },
        )
        response = _send_message(db_manager_socket, message)
        return response

    @control.doc(body=model_control_database)
    def delete(self) -> Response:
        """Delete a database."""
        message = Request(
            header=Header(message="delete database"),
            body={"id": control.payload["id"]},
        )
        response = _send_message(db_manager_socket, message)
        return response


@control.route("/workload", methods=["POST", "DELETE"])
class Workload(Resource):
    """Manages workload generation."""

    def post(self) -> Response:
        """Start the workload generator."""
        message = Request(header=Header(message="start worker"), body={})
        response = _send_message(db_manager_socket, message)
        if response["header"]["status"] != 200:
            return get_error_response(
                400, response["body"].get("error", "Error during starting of worker")
            )

        message = Request(
            header=Header(message="start workload"),
            body={
                "folder_name": control.payload["folder_name"],
                "frequency": control.payload.get("frequency", 200),
            },
        )
        response = _send_message(generator_socket, message)
        if response["header"]["status"] != 200:
            return get_error_response(
                400,
                response["body"].get("error", "Error during starting of the workload"),
            )

        return get_response(200)

    def delete(self) -> Response:
        """Stop the workload generator and empty database queues."""
        message = Request(header=Header(message="stop workload"), body={})
        response = _send_message(generator_socket, message)
        if response["header"]["status"] != 200:
            return get_error_response(
                400, response["body"].get("error", "Error during stopping of generator")
            )

        message = Request(header=Header(message="close worker"), body={})
        response = _send_message(db_manager_socket, message)
        if response["header"]["status"] != 200:
            return get_error_response(
                400, response["body"].get("error", "Error during closing of worker")
            )

        return response


@control.route("/data")
class Data(Resource):
    """Manage data in databases."""

    @control.doc(model=[model_data])
    def get(self) -> List[str]:
        """Return all pregenerated tables that can be loaded."""
        return ["tpch_0.1", "tpch_1", "tpcds_1", "job"]

    # @control.doc(body=model_data)
    def post(self) -> Response:
        """Load pregenerated tables for all databases."""
        message = Request(
            header=Header(message="load data"),
            body={"folder_name": control.payload["folder_name"]},
        )
        response = _send_message(db_manager_socket, message)
        return response

    @control.doc(body=model_data)
    def delete(self) -> Response:
        """Delete pregenerated tables from all databases."""
        message = Request(
            header=Header(message="delete data"),
            body={"folder_name": control.payload["folder_name"]},
        )
        response = _send_message(db_manager_socket, message)
        return response


@control.route("/available_plugins")
class ActivatedPlugin(Resource):
    """Get all available Plugins."""

    @control.doc(model=model_get_all_plugins)
    def get(self) -> List[str]:
        """Return available plugins."""
        return available_plugins


@control.route("/plugin")
class Plugin(Resource):
    """Activate, Deactive Plugins, respectively show which ones are activated."""

    @control.doc(model=[model_get_activated_plugins])
    def get(self) -> Union[Dict, List[Dict[str, List[str]]]]:
        """Return activated plugins in each database."""
        message = Request(header=Header(message="get plugins"), body={})
        response = _send_message(db_manager_socket, message)
        return response["body"]["plugins"]

    @control.doc(body=model_activate_plugin)
    def post(self) -> Response:
        """Activate a plugin in a database."""
        message = Request(
            header=Header(message="activate plugin"),
            body={"id": control.payload["id"], "plugin": control.payload["plugin"]},
        )
        response = _send_message(db_manager_socket, message)
        return response

    @control.doc(body=model_deactivate_plugin)
    def delete(self) -> Response:
        """Deactivate a plugin in a database."""
        message = Request(
            header=Header(message="deactivate plugin"),
            body={"id": control.payload["id"], "plugin": control.payload["plugin"]},
        )
        response = _send_message(db_manager_socket, message)
        return response


@control.route("/plugin_log")
class PluginLog(Resource):
    """Activate, Deactive Plugins, respectively show which ones are activated."""

    @api.doc(model=[model_plugin_log])
    def get(self) -> List[Dict[str, Union[str, List[Dict[str, Union[str, int]]]]]]:
        """Return activated plugins in each database."""
        return [
            {
                "id": database,
                "plugin_log": [
                    {
                        "timestamp": row["timestamp"],
                        "reporter": row["reporter"],
                        "message": row["message"],
                    }
                    for row in list(
                        storage_connection.query(
                            "SELECT timestamp, reporter, message from plugin_log;",
                            database=database,
                        )["plugin_log", None]
                    )
                ],
            }
            for database in _active_databases()
        ]


@control.route("/plugin_settings")
class PluginSettings(Resource):
    """Set settings for plugins."""

    @control.doc(model=[model_get_plugin_setting])  # TODO: fix model
    def get(self) -> Response:
        """Read settings for plugins."""
        message = Request(header=Header(message="get plugin setting"), body={},)
        response = _send_message(db_manager_socket, message)
        return response

    @control.doc(body=model_plugin_setting)
    def post(self) -> Response:
        """Set settings for plugins."""
        message = Request(
            header=Header(message="set plugin setting"),
            body={
                "id": control.payload["id"],
                "name": control.payload["name"],
                "value": control.payload["value"],
            },
        )
        response = _send_message(db_manager_socket, message)
        return response
