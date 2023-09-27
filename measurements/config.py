import json
import os
import re
import subprocess
import time
from dataclasses import dataclass
from typing import Literal

path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src_path = f"{path}/src"
FilterType = Literal["no", "basic", "blocked"]


@dataclass
class JoinConfig:
    """Represents configuration of one execution of the radix join"""

    algo: str = None
    nthreads: int = None
    r_size: int = None
    s_size: int = None
    r_seed: int = None
    s_seed: int = None
    s_sel: float = None
    skew: float = None
    r_file: str = None
    s_file: str = None
    non_unique: bool = None
    full_range: bool = None
    basic_numa: bool = None
    bloom_filter: FilterType = "no"
    bloom_hashes: int = None
    bloom_size: int = None
    bloom_block_size: int = None

    def toDict(self):
        return {key: value for key, value in self.getArgs()}

    def toJson(self):
        return json.dumps(self.toDict())

    @staticmethod
    def fromJson(data: str):
        return json.loads(data.replace("-", "_"), object_hook=lambda a: JoinConfig(**a))

    def getArgs(self):
        return [
            (key.replace("_", "-"), value)
            for key, value in self.__dict__.items()
            if value is not None
        ]

    def getBoolArgs(self):
        boolArgs = []
        if self.basic_numa:
            boolArgs += ["--basic-numa"]
        if self.full_range:
            boolArgs += ["--full-range"]
        if self.non_unique:
            boolArgs += ["--non-unique"]
        return boolArgs

    def getArgsString(self):
        """Returns a string representing the arguments that can be used for running the command"""
        return " ".join(
            [
                f'--{key}="{value}"'
                for key, value in self.getArgs()
                if not isinstance(value, bool)
            ]
            + self.getBoolArgs()
        )

    def getArgsList(self):
        """Returns the arguments as a list in the form of ["--key1", "value1", ...]"""
        return (
            "["
            + ", ".join(
                [
                    f'"--{key}", "{value}"'
                    for key, value in self.getArgs()
                    if not isinstance(value, bool)
                ]
                + [f'"{x}"' for x in self.getBoolArgs()]
            )
            + "]"
        )


CPU_MAPPINGS = {
    "Intel(R) Xeon(R) CPU E5-2690 0 @ 2.90GHz": {
        "single": "32 0 1 2 3 4 5 6 7 16 17 18 19 20 21 22 23 8 9 10 11 12 13 14 15 24 25 26 27 28 29 30 31",
        "numa": "32 0 8 1 9 2 10 3 11 4 12 5 13 6 14 7 15 16 24 17 25 18 26 19 27 20 28 21 29 22 30 23 31",
        "hypthr": "32 0 16 1 17 2 18 3 19 4 20 5 21 6 22 7 23 8 24 9 25 10 26 11 27 12 28 13 29 14 30 15 31",
        "all": "32 0 16 8 24 1 17 9 25 2 18 10 26 3 19 11 27 4 20 12 28 5 21 13 29 6 22 14 30 7 23 15 31",
    },
    "Intel(R) Xeon(R) CPU E5-2697 v3 @ 2.60GHz": {
        "single": "56 0 1 2 3 4 5 6 7 8 9 10 11 12 13 28 29 30 31 32 33 34 35 36 37 38 39 40 41 14 15 16 17 18 19 20 21 22 23 24 25 26 27 42 43 44 45 46 47 48 49 50 51 52 53 54 55",
        "numa": "56 0 14 1 15 2 16 3 17 4 18 5 19 6 20 7 21 8 22 9 23 10 24 11 25 12 26 13 27 28 42 29 43 30 44 31 45 32 46 33 47 34 48 35 49 36 50 37 51 38 52 39 53 40 54 41 55",
        "hypthr": "56 0 28 1 29 2 30 3 31 4 32 5 33 6 34 7 35 8 36 9 37 10 38 11 39 12 40 13 41 14 42 15 43 16 44 17 45 18 46 19 47 20 48 21 49 22 50 23 51 24 52 25 53 26 54 27 55",
        "all": "56 0 28 14 42 1 29 15 43 2 30 16 44 3 31 17 45 4 32 18 46 5 33 19 47 6 34 20 48 7 35 21 49 8 36 22 50 9 37 23 51 10 38 24 52 11 39 25 53 12 40 26 54 13 41 27 55",
    },
    "Intel(R) Xeon(R) Gold 6226 CPU @ 2.70GHz": {
        "single": "48 0 1 2 3 4 5 6 7 8 9 10 11 24 25 26 27 28 29 30 31 32 33 34 35 12 13 14 15 16 17 18 19 20 21 22 23 36 37 38 39 40 41 42 43 44 45 46 47",
        "numa": "48 0 12 1 13 2 14 3 15 4 16 5 17 6 18 7 19 8 20 9 21 10 22 11 23 24 36 25 37 26 38 27 39 28 40 29 41 30 42 31 43 32 44 33 45 34 46 35 47",
        "hypthr": "48 0 24 1 25 2 26 3 27 4 28 5 29 6 30 7 31 8 32 9 33 10 34 11 35 12 36 13 37 14 38 15 39 16 40 17 41 18 42 19 43 20 44 21 45 22 46 23 47",
        "all": "48 0 24 12 36 1 25 13 37 2 26 14 38 3 27 15 39 4 28 16 40 5 29 17 41 6 30 18 42 7 31 19 43 8 32 20 44 9 33 21 45 10 34 22 46 11 35 23 47",
    },
    "Intel(R) Xeon(R) Gold 6230 CPU @ 2.10GHz": {
        "single": "80 0 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 40 41 42 43 44 45 46 47 48 49 50 51 52 53 54 55 56 57 58 59 20 21 22 23 24 25 26 27 28 29 30 31 32 33 34 35 36 37 38 39 60 61 62 63 64 65 66 67 68 69 70 71 72 73 74 75 76 77 78 79",
        "numa": "80 0 20 1 21 2 22 3 23 4 24 5 25 6 26 7 27 8 28 9 29 10 30 11 31 12 32 13 33 14 34 15 35 16 36 17 37 18 38 19 39 40 60 41 61 42 62 43 63 44 64 45 65 46 66 47 67 48 68 49 69 50 70 51 71 52 72 53 73 54 74 55 75 56 76 57 77 58 78 59 79",
        "hypthr": "80 0 40 1 41 2 42 3 43 4 44 5 45 6 46 7 47 8 48 9 49 10 50 11 51 12 52 13 53 14 54 15 55 16 56 17 57 18 58 19 59 20 60 21 61 22 62 23 63 24 64 25 65 26 66 27 67 28 68 29 69 30 70 31 71 32 72 33 73 34 74 35 75 36 76 37 77 38 78 39 79",
        "all": "80 0 40 20 60 1 41 21 61 2 42 22 62 3 43 23 63 4 44 24 64 5 45 25 65 6 46 26 66 7 47 27 67 8 48 28 68 9 49 29 69 10 50 30 70 11 51 31 71 12 52 32 72 13 53 33 73 14 54 34 74 15 55 35 75 16 56 36 76 17 57 37 77 18 58 38 78 19 59 39 79",
    },
    "Intel(R) Xeon Phi(TM) CPU 7250 @ 1.40GHz": {
        "single": "272 0 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30 31 32 33 34 35 36 37 38 39 40 41 42 43 44 45 46 47 48 49 50 51 52 53 54 55 56 57 58 59 60 61 62 63 64 65 66 67 68 69 70 71 72 73 74 75 76 77 78 79 80 81 82 83 84 85 86 87 88 89 90 91 92 93 94 95 96 97 98 99 100 101 102 103 104 105 106 107 108 109 110 111 112 113 114 115 116 117 118 119 120 121 122 123 124 125 126 127 128 129 130 131 132 133 134 135 136 137 138 139 140 141 142 143 144 145 146 147 148 149 150 151 152 153 154 155 156 157 158 159 160 161 162 163 164 165 166 167 168 169 170 171 172 173 174 175 176 177 178 179 180 181 182 183 184 185 186 187 188 189 190 191 192 193 194 195 196 197 198 199 200 201 202 203 204 205 206 207 208 209 210 211 212 213 214 215 216 217 218 219 220 221 222 223 224 225 226 227 228 229 230 231 232 233 234 235 236 237 238 239 240 241 242 243 244 245 246 247 248 249 250 251 252 253 254 255 256 257 258 259 260 261 262 263 264 265 266 267 268 269 270 271",
        "hypthr": "272 0 68 136 204 1 69 137 205 2 70 138 206 3 71 139 207 4 72 140 208 5 73 141 209 6 74 142 210 7 75 143 211 8 76 144 212 9 77 145 213 10 78 146 214 11 79 147 215 12 80 148 216 13 81 149 217 14 82 150 218 15 83 151 219 16 84 152 220 17 85 153 221 18 86 154 222 19 87 155 223 20 88 156 224 21 89 157 225 22 90 158 226 23 91 159 227 24 92 160 228 25 93 161 229 26 94 162 230 27 95 163 231 28 96 164 232 29 97 165 233 30 98 166 234 31 99 167 235 32 100 168 236 33 101 169 237 34 102 170 238 35 103 171 239 36 104 172 240 37 105 173 241 38 106 174 242 39 107 175 243 40 108 176 244 41 109 177 245 42 110 178 246 43 111 179 247 44 112 180 248 45 113 181 249 46 114 182 250 47 115 183 251 48 116 184 252 49 117 185 253 50 118 186 254 51 119 187 255 52 120 188 256 53 121 189 257 54 122 190 258 55 123 191 259 56 124 192 260 57 125 193 261 58 126 194 262 59 127 195 263 60 128 196 264 61 129 197 265 62 130 198 266 63 131 199 267 64 132 200 268 65 133 201 269 66 134 202 270 67 135 203 271",
        "all": "272 0 68 136 204 1 69 137 205 2 70 138 206 3 71 139 207 4 72 140 208 5 73 141 209 6 74 142 210 7 75 143 211 8 76 144 212 9 77 145 213 10 78 146 214 11 79 147 215 12 80 148 216 13 81 149 217 14 82 150 218 15 83 151 219 16 84 152 220 17 85 153 221 18 86 154 222 19 87 155 223 20 88 156 224 21 89 157 225 22 90 158 226 23 91 159 227 24 92 160 228 25 93 161 229 26 94 162 230 27 95 163 231 28 96 164 232 29 97 165 233 30 98 166 234 31 99 167 235 32 100 168 236 33 101 169 237 34 102 170 238 35 103 171 239 36 104 172 240 37 105 173 241 38 106 174 242 39 107 175 243 40 108 176 244 41 109 177 245 42 110 178 246 43 111 179 247 44 112 180 248 45 113 181 249 46 114 182 250 47 115 183 251 48 116 184 252 49 117 185 253 50 118 186 254 51 119 187 255 52 120 188 256 53 121 189 257 54 122 190 258 55 123 191 259 56 124 192 260 57 125 193 261 58 126 194 262 59 127 195 263 60 128 196 264 61 129 197 265 62 130 198 266 63 131 199 267 64 132 200 268 65 133 201 269 66 134 202 270 67 135 203 271",
    },
}
"""
For each CPU, this defines a number of interesting configurations for cpu-mapping.txt, which assigns threads to logical cpus. The parameter are meant as follows:
`single`: aim for one thread per physical core, i.e., prevent hyperthreading at the cost of NUMA
`numa`: aim for equal distribution across all numa regions, hyperthreading only if there are no free physical cores
`hypthr`: aim for instant hyperthreading, i.e., fully occupy a physical core before moving to the next one
`all`: equally distribute threads across all numa regions with hyperthreading enabled
"""

CPU_THREAD_STEP_CONFIG = {
    "Intel(R) Xeon(R) CPU E5-2690 0 @ 2.90GHz": [
        (8, 1, "single"),
        (16, 2, "hypthr"),
        (16, 2, "numa"),
        (32, 4, "all"),
    ],
    "Intel(R) Xeon(R) CPU E5-2697 v3 @ 2.60GHz": [
        (14, 1, "single"),
        (28, 2, "hypthr"),
        (28, 2, "numa"),
        (56, 4, "all"),
    ],
    "Intel(R) Xeon(R) Gold 6226 CPU @ 2.70GHz": [
        (12, 1, "single"),
        (24, 2, "hypthr"),
        (24, 2, "numa"),
        (48, 4, "all"),
    ],
    "Intel(R) Xeon(R) Gold 6230 CPU @ 2.10GHz": [
        (20, 1, "single"),
        (40, 2, "hypthr"),
        (40, 2, "numa"),
        (80, 4, "all"),
    ],
    "Intel(R) Xeon Phi(TM) CPU 7250 @ 1.40GHz": [
        (68, 4, "single"),
        (272, 16, "hypthr"),
        (272, 16, "all"),  # there is only 1 numa node, so SMT and all will be the same
    ],
}
"""For each CPU, this defines different thread step sizes to consider when running exhaustive evaluation.
Each entry consists of (max_threads, step_size, cpu_mapping).
The step size is not fixed and only depends on the desired granularity of test results.
However, decreasing the step size results in more runs and thus significantly more runtime
"""


def get_cpu_thread_step_config(cpu: str = None):
    """Returns the thread step config for a given or the current cpu if none is specified.
    This consist of a list of (max_threads, step_size, cpu_mapping) entries.

    Args:
        cpu (str, optional): the cpu to be queried.

    Raises:
        ValueError: If there is no configuration for cpu or the CPU could not be found

    Returns:
        _type_: _description_
    """
    if cpu is None:
        cpu = get_cpu()
    if cpu not in CPU_THREAD_STEP_CONFIG:
        raise ValueError(
            f"Thread step configuration not found for CPU '{cpu}', please specify configuration first"
        )
    return CPU_THREAD_STEP_CONFIG[cpu]


CpuMappingType = Literal["single", "numa", "hypthr", "all"]

cpu_mapping_curr: CpuMappingType = None


def set_cpu_mapping(mapping: CpuMappingType, cpu: str = None):
    """Sets the CPU mapping to `mapping` for the specified CPU.
    If cpu is not given, this function tries to find the cpu by
    calling `get_cpu()`

    Args:
        mapping (CpuMappingType): The CPU mapping to set
        cpu (str, optional): the name of the CPU.

    Raises:
        ValueError: if the mapping could not be found for the cpu or no cpu was found
    """
    if cpu is None:
        cpu = get_cpu()
    if cpu not in CPU_MAPPINGS or mapping not in CPU_MAPPINGS[cpu]:
        raise ValueError(
            f"Unknown CPU mapping '{mapping}' for CPU '{cpu}', please specify CPU mappings for this CPU first"
        )

    with open(f"{src_path}/cpu-mapping.txt", "w") as file:
        global cpu_mapping_curr
        cpu_mapping_curr = mapping
        file.write(CPU_MAPPINGS[cpu][mapping])


def get_cpu() -> str:
    """Extract the CPU model name from `lscpu`

    Raises:
        ValueError: If `lscpu` does not print the Model name

    Returns:
        str: the CPU model name
    """
    p = subprocess.run("lscpu", capture_output=True, check=True, shell=True)
    match = re.search(r"Model name:[ \t]*([^\n]*)\n", p.stdout.decode())
    if match:
        return match.group(1)
    else:
        raise ValueError("argument 'cpu' not given and cannot be automatically derived")


def backup_cpu_mapping() -> str:
    """Backs up the current `cpu-mapping.txt` file to the returned filename

    Returns:
        str: the file that contains the backup
    """
    try:
        backup = f"__cpu-mapping_{time.time()*1000}.tmp"
        os.rename(f"{src_path}/cpu-mapping.txt", f"{src_path}/{backup}")
        return backup
    except OSError:
        return None


def restore_cpu_mapping(name: str):
    """Update the CPU configuration to the previously backuped configuration with filename `src/<name>`

    Args:
        name (str): name of the backup configuration file to be restored
    """
    global cpu_mapping_curr
    cpu_mapping_curr = None
    try:
        os.remove(f"{src_path}/cpu-mapping.txt")
    except OSError:
        pass
    if name:
        try:
            os.rename(f"{src_path}/{name}", f"{src_path}/cpu-mapping.txt")
        except OSError:
            pass


@dataclass
class PrjParam:
    """Container for possible parameters of `prj_params.h` and theri values"""

    name: str = ""
    value: "str | int" = None


prj_params_curr: "list[PrjParam]" = []


def set_prj_params(params: "list[PrjParam]" = [], reset=False) -> "list[PrjParam]":
    """Update `prj_params.h` file with the given params

    Args:
        params (list[PrjParam], optional): list of parameters to update to the value
        reset (bool, optional): whether this is a call that reset the configuration.

    Returns:
        list[PrjParam]: _description_
    """
    global prj_params_curr
    prj_params_curr = []
    old_params = []
    config = ""
    with open(f"{src_path}/prj_params.h", "r") as file:
        config = file.read()

    for param in params:
        pattern = rf"#define {param.name} ([0-9]+)"
        replace = f"#define {param.name} {param.value}"
        match = re.search(pattern, config)
        if match:
            config = re.sub(pattern, replace, config)
            old_params += [PrjParam(param.name, match.group(1))]
            prj_params_curr += [param]

    with open(f"{src_path}/prj_params.h", "w") as file:
        file.write(config)

    if reset:
        prj_params_curr = []

    return old_params


def set_cpu_constant():
    """Set the constant of the CPU that the program is running on in `cpu_mapping.c`
    """
    cpu = get_cpu()
    cpu_id = re.match(r".*([0-9]{4}).*", cpu).group(1)
    content = ""
    with open(f"{src_path}/cpu_mapping.c", "r") as file:
        content = file.read()

    base_pattern = rf"#define ((INTEL_XEON_E5_)|(INTEL_XEON_GOLD_)|(INTEL_XEON_PHI_)){cpu_id}"
    match = re.search(f"({base_pattern}) 0", content).group(1)
    content = re.sub(f"{match} 0", f"{match} 1", content)

    with open(f"{src_path}/cpu_mapping.c",  "w") as file:
        file.write(content)


def get_static_conf() -> dict:
    """Return configuration parameters that cannot be configured via the commandline

    Returns:
        dict: configured parameters and their values
    """
    ret = {}
    if cpu_mapping_curr is not None:
        ret["cpu-mapping"] = cpu_mapping_curr
    for prj_param in prj_params_curr:
        ret[prj_param.name] = prj_param.value
    return ret
