import { Fragment } from 'react';
import { Dialog, Transition } from '@headlessui/react';
import { X } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { useTheme } from '../../context/ThemeContext';

export default function Modal({ open, onClose, title, children, size = 'md' }) {
  const { t } = useTranslation();
  const { theme } = useTheme();

  const sizeClasses = {
    sm: 'max-w-sm',
    md: 'max-w-lg',
    lg: 'max-w-2xl',
    xl: 'max-w-4xl',
    full: 'max-w-full mx-4'
  };

  return (
    <Transition appear show={open} as={Fragment}>
      <Dialog as="div" className="relative z-50" onClose={onClose}>
        <Transition.Child
          as={Fragment}
          enter="ease-out duration-300"
          enterFrom="opacity-0"
          enterTo="opacity-100"
          leave="ease-in duration-200"
          leaveFrom="opacity-100"
          leaveTo="opacity-0"
        >
          <div className={`fixed inset-0 backdrop-blur-sm transition-colors ${theme === "dark" ? 'bg-slate-900/60' : 'bg-black/25'}`} />
        </Transition.Child>

        <div className="fixed inset-0 overflow-y-auto">
          <div className="flex min-h-full items-center justify-center p-4 text-center">
            <Transition.Child
              as={Fragment}
              enter="ease-out duration-300"
              enterFrom="opacity-0 scale-95"
              enterTo="opacity-100 scale-100"
              leave="ease-in duration-200"
              leaveFrom="opacity-100 scale-100"
              leaveTo="opacity-0 scale-95"
            >
              <Dialog.Panel className={`w-full ${sizeClasses[size]} transform overflow-hidden rounded-2xl text-left align-middle shadow-xl transition-all ${theme === "dark" ? 'bg-slate-800 border border-slate-700' : 'bg-white'}`}>
                <div className={`flex items-center justify-between p-6 border-b ${theme === "dark" ? 'border-slate-700' : 'border-slate-100'}`}>
                  <Dialog.Title as="h3" className={`text-lg font-semibold leading-6 ${theme === "dark" ? 'text-slate-100' : 'text-slate-900'}`}>
                    {title}
                  </Dialog.Title>
                  <button
                    type="button"
                    className={`rounded-full p-1 transition-colors ${theme === "dark" ? 'text-slate-400 hover:bg-slate-700 hover:text-slate-200' : 'text-slate-400 hover:bg-slate-100 hover:text-slate-600'}`}
                    onClick={onClose}
                    aria-label={t("common.close")}
                  >
                    <X className="h-5 w-5" />
                  </button>
                </div>
                <div className="p-6">
                  {children}
                </div>
              </Dialog.Panel>
            </Transition.Child>
          </div>
        </div>
      </Dialog>
    </Transition>
  );
}
