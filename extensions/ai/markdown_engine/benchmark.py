import time
from collections import defaultdict
import os

class BenchmarkTimer:
    def __init__(self, name, enabled=True, parent=None, log_file="bench.txt", sample_rate=1.0):
        self.name = name
        self.enabled = enabled
        self.parent = parent
        self.start_time = None
        self.end_time = None
        self.children = defaultdict(list)
        self.total_time = 0
        self.count = 0
        self.log_file = log_file
        self.raw_timings = []
        self.current_context = {}
        self.sample_rate = sample_rate
        self._sample_counter = 0
    
    def __enter__(self):
        if self.enabled:
            self._sample_counter += 1
            if self.sample_rate >= 1.0 or (self._sample_counter / self.sample_rate).is_integer():
                self.start_time = time.perf_counter()
                self.current_context = {}
            else:
                self.start_time = None
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.enabled and self.start_time is not None:
            self.end_time = time.perf_counter()
            duration_ms = (self.end_time - self.start_time) * 1000
            self.total_time += duration_ms
            self.count += 1
            self.raw_timings.append((duration_ms, self.current_context.copy()))
            if self.parent:
                self.parent.children[self.name].append(self)
    
    def child(self, name, sample_rate=None):
        rate = sample_rate if sample_rate is not None else self.sample_rate
        return BenchmarkTimer(name, enabled=self.enabled, parent=self, log_file=self.log_file, sample_rate=rate)
    
    def set_context(self, **kwargs):
        """Store contextual information about this timing"""
        if self.enabled:
            self.current_context.update(kwargs)
    
    def record_time(self, duration_ms, context=None):
        """Manually record a time in milliseconds"""
        if self.enabled:
            self._sample_counter += 1
            if self.sample_rate >= 1.0 or (self._sample_counter / self.sample_rate).is_integer():
                self.total_time += duration_ms
                self.count += 1
                ctx = self.current_context.copy() if context is None else {**self.current_context, **context}
                self.raw_timings.append((duration_ms, ctx))
                if self.parent:
                    self.parent.children[self.name].append(self)
    
    def print_summary(self, indent=0):
        if not self.enabled or (self.count == 0 and not self.children):
            return
        
        prefix = "  " * indent
        if self.count > 0:
            if self.count > 1:
                print(f"{prefix}{self.name}: {self.total_time:.2f}ms (x{self.count} runs, avg {self.total_time/self.count:.2f}ms)")
            else:
                print(f"{prefix}{self.name}: {self.total_time:.2f}ms")
        
        for child_name, timers in self.children.items():
            total_time = sum(t.total_time for t in timers)
            count = len(timers)
            if count > 1:
                print(f"{prefix}  - {child_name}: {total_time:.2f}ms (x{count} runs, avg {total_time/count:.2f}ms)")
            else:
                print(f"{prefix}  - {child_name}: {total_time:.2f}ms")
    
    def log_raw_data(self, file_path, depth=0):
        """Write raw timing data to file with hierarchical structure"""
        if not self.enabled:
            return
        
        with open(file_path, 'a', encoding='utf-8') as f:
            indent = "  " * depth
            
            # Write header for this timer
            f.write(f"{indent}=== {self.name} ===\n")
            f.write(f"{indent}Total: {self.total_time:.2f}ms, Count: {self.count}\n")
            
            # Write raw timings with context
            if self.raw_timings:
                f.write(f"{indent}Raw Timings:\n")
                for i, (duration, context) in enumerate(self.raw_timings):
                    f.write(f"{indent}  [{i+1}] {duration:.4f}ms")
                    if context:
                        ctx_str = ", ".join(f"{k}={v}" for k, v in context.items())
                        f.write(f" | {ctx_str}")
                    f.write("\n")
            
            # Write all child timers
            if self.children:
                for child_name, child_timers in self.children.items():
                    for timer in child_timers:
                        timer.log_raw_data(file_path, depth + 1)
                f.write("\n")

_global_benchmark = None

def get_global_benchmark():
    global _global_benchmark
    return _global_benchmark

def enable_global_benchmark(log_file="bench.txt"):
    global _global_benchmark
    _global_benchmark = BenchmarkTimer("TOTAL", enabled=True, log_file=log_file)
    return _global_benchmark

def disable_global_benchmark():
    global _global_benchmark
    _global_benchmark = None

def benchmark(name):
    def decorator(func):
        def wrapper(*args, **kwargs):
            global _global_benchmark
            if _global_benchmark:
                timer = _global_benchmark.child(name)
                with timer:
                    return func(*args, **kwargs)
            else:
                return func(*args, **kwargs)
        return wrapper
    return decorator
