from __future__ import annotations


import base64
import io
import logging
from typing import Literal

from langchain_core.tools import tool
from pydantic import BaseModel, Field, model_validator


logger = logging.getLogger(__name__)

chartType = Literal["bar", "line", "pie"]

class ChartInput