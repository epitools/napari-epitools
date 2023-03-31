"""
This module contains functions for calculating region-based properties
of labelled images using skimage.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import napari.types
    import numpy.typing as npt

import napari
import networkx.exception
import numpy as np
import skimage.graph
import skimage.measure

logger = logging.getLogger(__name__)


def calculate_cell_statistics(
    image: napari.types.ImageData,
    labels: napari.types.LabelsData,
) -> tuple[list[dict[str, npt.NDArray]], list[skimage.graph._rag.RAG]]:
    """Calculate the region based properties of a segmented image"""

    # Calculate cell statistics for each frame
    cell_statistics = _calculate_cell_statistics(image, labels)

    # Create graph of neighbouring cells at each frame
    graphs = _create_graphs(labels)

    # Calculate additional statistics from the graph
    # Update 'cell_statistics' in place
    _calculate_graph_statistics(
        cell_statistics,
        graphs,
    )

    return cell_statistics, graphs


def _calculate_cell_statistics(
    image: napari.types.ImageData,
    labels: napari.types.LabelsData,
) -> list[dict[str, npt.NDArray]]:
    """Calculate cell properties using skimage regionprops"""

    properties = ["label", "area", "perimeter", "orientation"]

    cell_statistics = [
        skimage.measure.regionprops_table(
            label_image=frame_labels,
            intensity_image=frame_image,
            properties=properties,
        )
        for frame_labels, frame_image in zip(labels, image)
    ]

    # skimage uses 'label' for what napari calls 'index'
    for frame_stats in cell_statistics:
        frame_stats["index"] = frame_stats.pop("label")

    return cell_statistics


def _create_graphs(
    labels: napari.types.LabelsData,
) -> skimage.graph._rag.RAG:
    """Create graph of neighbouring cells"""

    graphs = [skimage.graph.RAG(frame_labels) for frame_labels in labels]

    # remove the background if it exists
    for index, graph in enumerate(graphs):
        try:
            graph.remove_node(0)
        except networkx.exception.NetworkXError:
            message = f"No background node to remove for graph at frame {index}"
            logger.debug(message)

    return graphs


def _calculate_graph_statistics(
    cell_statistics: list[dict[str, npt.NDArray]],
    graphs: skimage.graph._rag.RAG,
) -> None:
    """Calcualte additional cell statistics from graphs.

    Adds results directly to 'cell_statistics' dictionaries.
    """

    for frame, (stats, graph) in enumerate(zip(cell_statistics, graphs)):
        indices = stats["index"]

        num_neighbours = np.asarray([len(graph[index]) for index in indices])
        cell_statistics[frame]["neighbours"] = num_neighbours
