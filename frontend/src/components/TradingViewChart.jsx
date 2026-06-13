import { useEffect, useRef } from 'react';

/**
 * Embeds the TradingView Advanced Chart widget into a container div.
 * Dynamically loads tv.js and initialises the widget.
 *
 * @param {string} symbol  - e.g. "NSE:RELIANCE" or "BSE:TATASTEEL"
 * @param {string} theme   - "dark" | "light"
 */
export default function TradingViewChart({ symbol, theme = 'dark' }) {
  const containerRef = useRef(null);
  const widgetRef    = useRef(null);

  useEffect(() => {
    if (!symbol || !containerRef.current) return;

    // Remove previous widget
    containerRef.current.innerHTML = '';

    const containerId = `tv_chart_${Math.random().toString(36).slice(2)}`;
    const div = document.createElement('div');
    div.id = containerId;
    div.style.height = '100%';
    containerRef.current.appendChild(div);

    const initWidget = () => {
      if (!window.TradingView) return;
      widgetRef.current = new window.TradingView.widget({
        autosize:           true,
        symbol:             symbol,
        interval:           'D',
        timezone:           'Asia/Kolkata',
        theme:              theme,
        style:              '1',
        locale:             'en',
        toolbar_bg:         '#111827',
        enable_publishing:  false,
        hide_side_toolbar:  false,
        allow_symbol_change: true,
        container_id:       containerId,
        studies: [
          'MASimple@tv-basicstudies',   // 50 MA
          'MASimple@tv-basicstudies',   // 200 MA
          'Volume@tv-basicstudies',
        ],
        overrides: {
          'mainSeriesProperties.candleStyle.upColor':   '#10b981',
          'mainSeriesProperties.candleStyle.downColor': '#ef4444',
          'mainSeriesProperties.candleStyle.borderUpColor':   '#10b981',
          'mainSeriesProperties.candleStyle.borderDownColor': '#ef4444',
          'mainSeriesProperties.candleStyle.wickUpColor':   '#10b981',
          'mainSeriesProperties.candleStyle.wickDownColor': '#ef4444',
        },
      });
    };

    // Load TV script once, then init
    if (window.TradingView) {
      initWidget();
    } else {
      const existing = document.getElementById('tv-script');
      if (!existing) {
        const script = document.createElement('script');
        script.id  = 'tv-script';
        script.src = 'https://s3.tradingview.com/tv.js';
        script.async = true;
        script.onload = initWidget;
        document.head.appendChild(script);
      } else {
        existing.addEventListener('load', initWidget);
      }
    }

    return () => {
      if (widgetRef.current && widgetRef.current.remove) {
        widgetRef.current.remove();
      }
    };
  }, [symbol, theme]);

  return (
    <div ref={containerRef} style={{ width: '100%', height: '100%' }} />
  );
}
