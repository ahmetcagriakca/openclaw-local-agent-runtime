"""Working set schema — defines bounded file access for each agent stage."""
from dataclasses import dataclass, field


@dataclass
class ReadBudget:
    """Tracks remaining read operations for a stage."""
    max_file_reads: int = 20
    max_directory_reads: int = 10
    max_expansions: int = 3
    remaining_file_reads: int = 20
    remaining_directory_reads: int = 10
    remaining_expansions: int = 3

    def consume_file_read(self) -> bool:
        """Consume one file read. Returns False if budget exhausted."""
        if self.remaining_file_reads <= 0:
            return False
        self.remaining_file_reads -= 1
        return True

    def consume_directory_read(self) -> bool:
        """Consume one directory read. Returns False if budget exhausted."""
        if self.remaining_directory_reads <= 0:
            return False
        self.remaining_directory_reads -= 1
        return True

    def consume_expansion(self) -> bool:
        """Consume one expansion. Returns False if budget exhausted."""
        if self.remaining_expansions <= 0:
            return False
        self.remaining_expansions -= 1
        return True


@dataclass
class FileAccess:
    """Defines which files/directories a role may access."""
    read_only: list[str] = field(default_factory=list)       # absolute canonical paths
    read_write: list[str] = field(default_factory=list)      # existing files role may modify
    creatable: list[str] = field(default_factory=list)       # new files role may create
    generated_outputs: list[str] = field(default_factory=list)  # artifact output locations
    directory_list: list[str] = field(default_factory=list)  # directories role may list


@dataclass
class WorkingSet:
    """Bounded working set for a single agent stage."""
    stage_id: str
    role: str
    skill: str = ""
    files: FileAccess = field(default_factory=FileAccess)
    budget: ReadBudget = field(default_factory=ReadBudget)
    forbidden_directories: list[str] = field(default_factory=list)
    forbidden_patterns: list[str] = field(default_factory=list)
