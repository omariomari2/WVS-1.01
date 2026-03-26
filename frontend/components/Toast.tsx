"use client";

import { useEffect, useRef, useState, useCallback } from "react";

export type ToastType = "info" | "success" | "error";

interface ToastMessage {
  id: number;
  text: string;
  type: ToastType;
}

let toastIdCounter = 0;
let globalShowToast: ((text: string, type?: ToastType) => void) | null = null;

export function showToast(text: string, type: ToastType = "info") {
  if (globalShowToast) globalShowToast(text, type);
}

function SingleToast({ message, onDone }: { message: ToastMessage; onDone: () => void }) {
  const [displayText, setDisplayText] = useState("");
  const indexRef = useRef(0);

  useEffect(() => {
    const interval = setInterval(() => {
      indexRef.current++;
      setDisplayText(message.text.substring(0, indexRef.current));
      if (indexRef.current >= message.text.length) {
        clearInterval(interval);
        setTimeout(onDone, 2500);
      }
    }, 30);
    return () => clearInterval(interval);
  }, [message.text, onDone]);

  return <div className={`toast toast-${message.type}`}>{displayText}</div>;
}

export default function ToastContainer() {
  const [messages, setMessages] = useState<ToastMessage[]>([]);

  const addToast = useCallback((text: string, type: ToastType = "info") => {
    const id = ++toastIdCounter;
    setMessages((prev) => [...prev, { id, text, type }]);
  }, []);

  useEffect(() => {
    globalShowToast = addToast;
    return () => {
      globalShowToast = null;
    };
  }, [addToast]);

  const removeToast = useCallback((id: number) => {
    setMessages((prev) => prev.filter((m) => m.id !== id));
  }, []);

  return (
    <>
      {messages.map((msg) => (
        <SingleToast
          key={msg.id}
          message={msg}
          onDone={() => removeToast(msg.id)}
        />
      ))}
    </>
  );
}
