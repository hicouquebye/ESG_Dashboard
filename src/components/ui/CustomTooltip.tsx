import React from 'react';

export const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
        return (
            <div className="bg-white/95 backdrop-blur-md border border-slate-100 p-4 rounded-xl shadow-2xl text-xs z-50">
                <p className="font-bold text-slate-800 mb-2 border-b border-slate-100 pb-2">{label}</p>
                {payload.map((entry: any, index: number) => (
                    <div key={index} className="flex items-center gap-2 mb-1 justify-between min-w-[120px]">
                        <div className="flex items-center gap-2">
                            <div className="w-2 h-2 rounded-full" style={{ backgroundColor: entry.color }} />
                            <span className="text-slate-500 font-medium capitalize">{entry.name}</span>
                        </div>
                        <span className="font-bold text-slate-900 font-mono">
                            {entry.name === 'EU-ETS' ? '€' : (entry.name === 'UK-ETS' ? '£' : '₩')}
                            {typeof entry.value === 'number' ? entry.value.toLocaleString() : entry.value}
                        </span>
                    </div>
                ))}
            </div>
        );
    }
    return null;
};
