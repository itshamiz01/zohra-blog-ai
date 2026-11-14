import React, { useState } from "react";
import { AlertOctagon, X } from "lucide-react";

interface ConfirmModalProps {
  isOpen: boolean;
  title: string;
  description: string;
  confirmLabel?: string;
  isDangerous?: boolean;
  defaultReason?: string;
  onConfirm: (reason: string) => void;
  onCancel: () => void;
}

export const ConfirmModal: React.FC<ConfirmModalProps> = ({
  isOpen,
  title,
  description,
  confirmLabel = "Confirm Action",
  isDangerous = true,
  defaultReason = "",
  onConfirm,
  onCancel,
}) => {
  const [reason, setReason] = useState("");

  React.useEffect(() => {
    if (isOpen) setReason(defaultReason);
  }, [isOpen, defaultReason]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
      <div className="w-full max-w-md p-6 bg-white border border-[#E7DCB8] rounded-2xl shadow-2xl">
        <div className="flex items-center justify-between pb-3 border-b border-[#E7DCB8]">
          <div className="flex items-center gap-2">
            {isDangerous && <AlertOctagon className="w-5 h-5 text-rose-500" />}
            <h3 className="text-base font-semibold text-[#123B2A]">{title}</h3>
          </div>
          <button onClick={onCancel} className="text-stone-500 hover:text-stone-800">
            <X className="w-5 h-5" />
          </button>
        </div>

        <p className="mt-3 text-sm text-stone-600">{description}</p>

        <div className="mt-4">
          <label className="block text-xs font-medium text-stone-500 mb-1">
            Reason (filled in for you — edit if you like)
          </label>
          <input
            type="text"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder="e.g. Incident #104 investigating WordPress latency"
            className="w-full px-3 py-2 text-sm bg-[#FAF9F5] border border-[#D8C78F] rounded-lg text-[#123B2A] placeholder-stone-400 focus:outline-none focus:border-[#C9A227]"
          />
        </div>

        <div className="flex justify-end gap-3 mt-6">
          <button
            onClick={onCancel}
            className="px-4 py-2 text-sm font-medium text-stone-600 hover:text-[#123B2A] hover:bg-[#EFE6C8] bg-[#F7F2E2] rounded-lg"
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
                ? "bg-[#EFE6C8] cursor-not-allowed opacity-50"
                : isDangerous
                ? "bg-rose-600 hover:bg-rose-700"
                : "bg-emerald-600 hover:bg-emerald-700"
            }`}
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
};
