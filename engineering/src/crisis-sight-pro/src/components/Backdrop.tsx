// 背景：几团缓慢漂移的渐变光晕 + 一层细网格，营造指挥大屏的底子

export function Backdrop() {
  return (
    <div className="pointer-events-none fixed inset-0 -z-10 overflow-hidden">
      <div className="absolute inset-0 bg-abyss-800" />

      {/* 网格 */}
      <div
        className="absolute inset-0 opacity-[0.22]"
        style={{
          backgroundImage:
            'linear-gradient(rgba(120,160,220,0.08) 1px, transparent 1px), linear-gradient(90deg, rgba(120,160,220,0.08) 1px, transparent 1px)',
          backgroundSize: '46px 46px',
          maskImage:
            'radial-gradient(ellipse 90% 70% at 50% 0%, #000 20%, transparent 78%)',
          WebkitMaskImage:
            'radial-gradient(ellipse 90% 70% at 50% 0%, #000 20%, transparent 78%)',
        }}
      />

      {/* 光晕 */}
      <div className="absolute -top-40 left-[8%] h-[420px] w-[420px] rounded-full bg-cyanline-500/20 blur-[130px] animate-drift" />
      <div
        className="absolute top-[18%] right-[4%] h-[380px] w-[380px] rounded-full bg-indigoink-500/20 blur-[130px] animate-drift"
        style={{ animationDelay: '2.2s' }}
      />
      <div
        className="absolute bottom-[-8%] left-[35%] h-[360px] w-[360px] rounded-full bg-amberwarn-500/10 blur-[140px] animate-drift"
        style={{ animationDelay: '4.4s' }}
      />

      {/* 顶部一道扫描光带 */}
      <div
        className="absolute inset-x-0 top-0 h-[2px] opacity-70 animate-sweep"
        style={{
          background:
            'linear-gradient(90deg, transparent, #22d3ee, #6366f1, transparent)',
          backgroundSize: '200% 100%',
        }}
      />
    </div>
  )
}
