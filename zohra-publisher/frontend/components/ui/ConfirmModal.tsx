import React, { useState } from "react";
import { AlertOctagon, X } from "lucide-react";

interface ConfirmModalProps {
  isOpen: boolean;
  title: string;
  description: string;
  confirmLabel?: string;
  isDangerous?: boolean;
  onConfirm: (reason: string) => void;
  onCancel: () => void;
}

export const ConfirmModal: React.FC<ConfirmModalProps> = ({
  isOpen,
  title,
  description,
  confirmLabel = "Confirm Action",
  isDangerous = true,
  onConfirm,
  onCancel,
}) => {
  const [reason, setReason] = useState("");

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
      <div className="w-full max-w-md p-6 bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl">
        <div className="flex items-center justify-between pb-3 border-b border-slate-800">
          <div className="flex items-center gap-2">
            {isDangerous && <AlertOctagon className="w-5 h-5 text-rose-500" />}
            <h3 className="text-base font-semibold text-slate-100">{title}</h3>
          </div>
          <button onClick={onCancel} className="text-slate-400 hover:text-slate-200">
            <X className="w-5 h-5" />
          </button>
        </div>

        <p className="mt-3 text-sm text-slate-300">{description}</p>

        <div className="mt-4">
          <label className="block text-xs font-medium text-slate-400 mb-1">
            Audited Operational Reason (Required)
          </label>
          <input
            type="text"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder="e.g. Incident #104 investigating WordPress latency"
            className="w-full px-3 py-2 text-sm bg-slate-950 border border-slate-700 rounded-lg text-slate-100 placeholder-slate-500 focus:outline-none focus:border-blue-500"
          />
        </div>

        <div className="flex justify-end gap-3 mt-6">
          <button
            onClick={onCancel}
            className="px-4 py-2 text-sm font-medium text-slate-300 hover:text-white bg-slate-800 rounded-lg"
          >
            Cancel
          </button>
          <button
            disabled={reason.trim().length < 5}
            onClick={() => {
              onConfirm(reason);
              setReason("");
            }}
            className={`px-4 py-2 text-sm font-medium rounded-lg text-white ${
              reason.trim().length < 5
                ? "bg-slate-700 cursor-not-allowed opacity-50"
                : isDangerous
                ? "bg-rose-600 hover:bg-rose-700"
                : "bg-blue-600 hover:bg-blue-700"
            }`}
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
};
