import React from 'react';
import { Leaf } from 'lucide-react';
import { Button } from '../ui/Button';
import type { TabType } from '../../types';

interface HeaderProps {
    activeTab: TabType;
    setActiveTab: (tab: TabType) => void;
    tabs: { id: TabType; label: string }[];
}

export const Header: React.FC<HeaderProps> = ({ activeTab, setActiveTab, tabs }) => {
    return (
        <nav className="bg-white/80 backdrop-blur-md border-b border-slate-100 px-8 py-4 flex justify-between items-center sticky top-0 z-30">
            <div className="flex items-center gap-3">
                <div className="p-2 rounded-xl text-[#10b77f]"><Leaf size={24} /></div>
                <span className="text-xl font-bold tracking-tight text-slate-800">ESG OS</span>
            </div>
            <div className="flex bg-slate-100/50 p-1 rounded-xl">
                {tabs.map(t => (
                    <Button key={t.id} variant={activeTab === t.id ? 'tabActive' : 'tab'} onClick={() => setActiveTab(t.id)}>{t.label}</Button>
                ))}
            </div>
        </nav>
    );
};
