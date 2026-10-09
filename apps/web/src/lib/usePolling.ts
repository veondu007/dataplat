import { useEffect, useRef } from "react";

/**
 * 轻量轮询 hook：enabled 时以 tickMs 间隔执行 onTick；shouldStop 返回 true 即停止，
 * 卸载时清理定时器。onTick/shouldStop 用 ref 保存避免闭包过期值。
 */
export function usePolling(
  enabled: boolean,
  tickMs: number,
  shouldStop: (count: number) => boolean,
  onTick: (count: number) => void,
): void {
  const tickRef = useRef(onTick);
  tickRef.current = onTick;
  const stopRef = useRef(shouldStop);
  stopRef.current = shouldStop;

  useEffect(() => {
    if (!enabled) return;
    let count = 0;
    let timer: number | undefined;

    const loop = () => {
      count += 1;
      tickRef.current(count);
      if (stopRef.current(count)) return; // 终态：停止，不再排下次
      timer = window.setTimeout(loop, tickMs);
    };

    // 首 tick 前先等一个周期，避免与触发动作取同一时刻
    timer = window.setTimeout(loop, tickMs);
    return () => {
      if (timer) window.clearTimeout(timer);
    };
  }, [enabled, tickMs]);
}