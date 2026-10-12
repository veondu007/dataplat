import { useEffect, useRef } from "react";
import * as echarts from "echarts";

/** 轻量 echarts React 封装：挂载时 init + 自适应 resize，option 变化即 setOption。 */
export function Chart({
  option,
  height = 320,
  loading = false,
}: {
  option: echarts.EChartsOption;
  height?: number;
  loading?: boolean;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const instRef = useRef<echarts.ECharts | null>(null);

  // 初始化实例（仅一次）
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const inst = echarts.init(el);
    instRef.current = inst;
    const ro = new ResizeObserver(() => inst.resize());
    ro.observe(el);
    return () => {
      ro.disconnect();
      inst.dispose();
      instRef.current = null;
    };
  }, []);

  // 数据/加载态变化时刷新
  useEffect(() => {
    const inst = instRef.current;
    if (!inst) return;
    if (loading) {
      inst.showLoading();
      return;
    }
    inst.hideLoading();
    inst.setOption(option, true);
  }, [option, loading]);

  return <div ref={ref} style={{ width: "100%", height }} />;
}