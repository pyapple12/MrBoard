# Qt 异步任务设施（A017/PL006.2）：把同步函数提交线程池后台执行，结果经信号
# 回传主线程——随前端生灭的传输层（内部零业务逻辑；换前端时本模块随之重写）

from collections import deque
from typing import Any, Callable

from PyQt6.QtCore import QObject, QRunnable, QThreadPool, pyqtSignal


class TaskRunner(QObject):
    # 统一后台任务运行器：成功发 finished(seq, 结果)、异常发 failed(seq, 异常串)；
    # 每个职责一个实例（usage/quota/data/export 各一），信号直连对应 handler 零分发

    finished = pyqtSignal(int, object)
    failed = pyqtSignal(int, str)

    def __init__(self, pool: QThreadPool, parent: QObject | None = None) -> None:
        # 初始化：注入线程池（MainWindow 的 self._pool），支持测试替换；
        # _live_tasks 持有执行中任务的 Python 引用；完成后转入 _done_tasks 继续保引用
        # （QRunnable wrapper 在 worker 运行期被 GC 会触发 0xC0000409 崩溃，
        # A017/PL006.2 实测教训——deque(maxlen) 自动淘汰最老引用无泄漏）
        super().__init__(parent)
        self._pool = pool
        self._live_tasks: set[_FnTask] = set()
        self._done_tasks: deque[_FnTask] = deque(maxlen=16)

    def run(self, fn: Callable[[], Any], *, seq: int = 0) -> None:
        # 提交同步函数到线程池：成功发 finished(seq, fn())、异常发 failed(seq, str(exc))；
        # ui.json 文案格式化留在 UI 层 handler（failed 载荷为原始异常串）
        task = _FnTask(self, fn, seq)
        task.setAutoDelete(False)  # A017/PL006.2：生命周期全权由 Python 侧管理
        self._live_tasks.add(task)
        self._pool.start(task)

    def _task_done(self, task: "_FnTask") -> None:
        # 任务完成回调：从执行中集合转入完成队列（保持 Python 引用防悬空）
        self._live_tasks.discard(task)
        self._done_tasks.append(task)


class _FnTask(QRunnable):
    # 线程池任务壳：执行 fn 并经 runner 信号回传结果/异常（QRunnable 无信号，
    # 经构造持有的 runner 引用发射——runner 由主线程持有不回收，引用安全）

    def __init__(self, runner: TaskRunner, fn: Callable[[], Any], seq: int) -> None:
        super().__init__()
        self._runner = runner
        self._fn = fn
        self._seq = seq

    def run(self) -> None:
        try:
            result = self._fn()
            self._runner.finished.emit(self._seq, result)
        except Exception as exc:
            self._runner.failed.emit(self._seq, str(exc))
        finally:
            self._runner._task_done(self)


# ===== ui/task_runner.py 模块说明 =====
# 职责：Qt 异步任务设施——把同步函数提交线程池后台执行，结果/异常经信号回传主线程；
#   随前端生灭的传输层（内部零业务逻辑，换前端时本模块随之重写）
# 类：
#   TaskRunner(QObject)：统一后台任务运行器；每个职责一个实例（usage/quota/data/export
#     各一），信号直连对应 handler 零分发；run(fn, seq=0) 提交任务
#   _FnTask(QRunnable)：线程池任务壳，执行 fn 并经持有的 runner 引用发射信号
#     （runner 由主线程持有不回收，引用安全；setAutoDelete(False) 生命周期全权由 Python 侧管理）
# 引用管理机制（A017/PL006.2 实测教训：QRunnable wrapper 运行期被 GC 触发 0xC0000409 崩溃）：
#   _live_tasks(set) 持有执行中任务 Python 引用；完成后转入 _done_tasks(deque maxlen=16)
#   继续保引用，自动淘汰最老且无泄漏
# 设计理由：网络 IO 不持锁、并发去重由业务模块（go_quota/opencode_data）各自标志+锁负责；
#   本模块只解决"异步执行+线程安全回传"，职责单一
