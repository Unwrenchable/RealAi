"use client";

import { useState } from "react";
import { Mic, MicOff } from "lucide-react";

export default function VoiceFab() {
  const [isRecording, setIsRecording] = useState(false);

  const toggleRecording = () => {
    setIsRecording(!isRecording);
    // TODO: Implement actual voice recording and processing
    console.log(isRecording ? "Stopped recording" : "Started recording");
  };

  return (
    <div className="fixed bottom-6 right-6 z-50">
      <button
        onClick={toggleRecording}
        className={`w-16 h-16 rounded-full flex items-center justify-center text-white font-medium transition-all ${
          isRecording
            ? "bg-red-600 hover:bg-red-500 animate-pulse"
            : "bg-violet-600 hover:bg-violet-500"
        } shadow-lg hover:shadow-xl`}
      >
        {isRecording ? <MicOff className="w-6 h-6" /> : <Mic className="w-6 h-6" />}
      </button>
    </div>
  );
}