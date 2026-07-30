from memory.memory import Memory
from memory.vector_memory import VectorMemory
from memory.memory_manager import MemoryManager
from memory.memory_validator import MemoryValidator
from memory.memory_consolidation import MemoryConsolidation
from memory.memory_lifecycle import MemoryLifecycle
from memory.background_workers import MemoryBackgroundWorker


def bootstrap_memory(runtime):
    memory = Memory()
    runtime.container.memory = memory

    vector_memory = VectorMemory(memory)
    runtime.container.vector_memory = vector_memory

    memory_manager = MemoryManager( memory, vector_memory)
    runtime.container.memory_manager = memory_manager

    validator = MemoryValidator()
    runtime.container.validator = validator

    consolidation = MemoryConsolidation(memory, vector_memory)
    runtime.container.consolidation = consolidation

    memory_lifecycle = MemoryLifecycle(memory_manager)
    runtime.container.memory_lifecycle = memory_lifecycle

    background_worker = MemoryBackgroundWorker(
        lifecycle=memory_lifecycle,
        consolidation=consolidation,
        brain=runtime.container.brain,
        memory_manager=memory_manager,
        interval_seconds=60,
    )
    runtime.container.background_worker = background_worker