from __future__ import annotations


import base64
import io
import logging
from typing import Literal

from langchain_core.tools import tool
from pydantic import BaseModel, Field, model_validator


logger = logging.getLogger(__name__)

ChartType = Literal["bar", "line", "pie"]

class ChartInput(BaseModel):
    chart_type: ChartType = Field(description="One of: bar, line, pi.")
    labels: list[str] = Field(
        min_length=1,
        max_length=50,
        description="Category labels (x-axis for bar/line, slice for pi).",
    )
    values: list[float] = Field(
        min_length=1,
        max_length=50,
        description="Numeric Values aligned with labels (same length).",
    )
    title: str = Field(default="", max_length=120, description="Chart Title")
    x_label: str = Field(default="", max_length=60, description="X-axis label")
    y_label: str = Field(default="", max_length=60, description="Y-axis label")
    
    @model_validator(mode="after")
    def _check_lengths(self) -> "ChartInput":
        if len(self.labels) != len(self.values):
            raise ValueError("labels and values must have the same length.")
        return self
    
    

def _render_png(payload: ChartInput) -> bytes:
    import matplotlib
    
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    
    
    fig, ax = plt.subplots(figsize=(8,5))
    try:
        if payload.chart_type == "bar":
            ax.bar(payload.labels, payload.values)
        elif payload.chart_type== "line":
            ax.plot(payload.labels, payload.values, marker="o")
        else:
            ax.pie(payload.values, labels= payload.labels, autopct="%1.1f%%")
            ax.set_aspect("equal")
            
        if payload.title:
            ax.set_title(payload.title)
        if payload.chart_type != "pie":
            if payload.x_label:
                ax.set_xlabel(payload.x_label)
            if payload.y_label:
                ax.set_ylabel(payload.y_label)
            fig.autofmt_xdate(rotation=30)
            
        fig.tight_layout()
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=120)
        return buf.getvalue()
    
    finally:
        plt.close(fig)
        

@tool(args_schema=ChartInput)
def generate_chart(
    chart_type: ChartType,
    labels: list[str],
    values:list[float],
    title: str="",
    x_label: str = "",
    y_label: str = "",
) -> str:
    """
    Render a chart from labelled numeric data and return a base64 PNG.
    
    Use this when a visualization would communicate the answer more clearly than text - ranked comparisons(bar), trends over an ordered axis(line), or proportions of a whole (pie). Provided aligned `lables` and `values` of the same length. Returns a `data:image/png;base64,...` URI that can be embedded directly in HTML or Markdown    
    """
    
    
    payload = ChartInput(
        chart_type=chart_type,
        labels=labels,
        values=values,
        title=title,
        x_label=x_label,
        y_label=y_label
    )
    
    try:
        png_bytes = _render_png(payload)
    except Exception as exc:
        logger.exception("Chart Rendering Failed")
        return f"Chart generation failed: {exc}"
    
    encoded = base64.b64encode(png_bytes).decode("ascii")
    return f"data:image/png;base64,{encoded}"