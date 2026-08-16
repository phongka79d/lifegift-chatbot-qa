import React, { useEffect, useRef } from 'react';

interface ProductRailProps {
  children: React.ReactNode;
  labelledBy?: string;
}

/** Horizontal snap rail. Vertical wheel maps to sideways scroll when the row overflows. */
export const ProductRail: React.FC<ProductRailProps> = ({ children, labelledBy }) => {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;

    const onWheel = (event: WheelEvent) => {
      if (el.scrollWidth <= el.clientWidth + 1) return;
      if (Math.abs(event.deltaY) <= Math.abs(event.deltaX)) return;
      event.preventDefault();
      el.scrollLeft += event.deltaY;
    };

    el.addEventListener('wheel', onWheel, { passive: false });
    return () => el.removeEventListener('wheel', onWheel);
  }, []);

  return (
    <div
      ref={ref}
      className="product-rail"
      role="list"
      aria-labelledby={labelledBy}
    >
      {children}
    </div>
  );
};
