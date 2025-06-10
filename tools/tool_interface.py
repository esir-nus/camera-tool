import abc
from utils.logging_config import setup_logging
from typing import Dict, Any, Optional
from utils.settings import Settings

# Set up a logger specific to this module
logger = setup_logging("tool_interface")

class ToolInterface(abc.ABC):
    """
    Abstract Base Class defining the core logic contract for a tool.
    Does not dictate execution context (threading, async).
    """

    def __init__(self, settings: Settings, tool_name: str):
        """
        Initializes the tool with its specific configuration.

        Args:
            settings: Application settings object.
            tool_name: A unique name identifying this tool instance.
        """
        self.settings = settings
        self.tool_name = tool_name
        logger.info(f"Initializing tool '{self.tool_name}'...")  # Use logger

    @abc.abstractmethod
    def initialize_tool(self) -> bool:
        """
        Perform any setup required for the tool before it can process commands.
        This might involve connecting to hardware, APIs, loading models, etc.
        Should be called by the runner *before* processing commands.

        Returns:
            True if initialization was successful, False otherwise.
        """
        pass

    @abc.abstractmethod
    def process_command(self, command_name: str, parameters: Dict[str, Any]) -> Any:
        """
        Processes a specific command directed at this tool.
        This method contains the core logic of the tool.
        It can be synchronous or asynchronous (if the tool is async).

        Args:
            command_name: The specific command/function the tool should execute.
            parameters: A dictionary of parameters for the command.

        Returns:
            Any result from the command execution, or None.
        """
        pass

    @abc.abstractmethod
    def shutdown_tool(self) -> None:
        """
        Perform any cleanup required when the tool is shutting down.
        This might involve disconnecting, releasing resources, etc.
        Should be called by the runner during the stop sequence.
        """
        pass

    def get_name(self) -> str:
        """Returns the name of the tool."""
        return self.tool_name
