import React, { useState } from "react";
import {
  FileImage,
  Brain,
  Database,
  ArrowRight,
  CheckCircle,
  MessageCircle,
} from "lucide-react";
import PIDUploadComponent from "./PIDUploadComponent";
import { useChat } from "../contexts/ChatContext";

const Index: React.FC = () => {
  const [showUpload, setShowUpload] = useState(false);
  const { openChat } = useChat();

  if (showUpload) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
        {/* Header */}
        <div className="bg-slate-800/50 backdrop-blur-sm border-b border-slate-700">
          <div className="max-w-7xl mx-auto px-6 py-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-4">
                <div className="w-14 h-14 rounded-lg flex items-center justify-center">
                  <img
                    src="/logo.png"
                    alt="APX GP"
                    className="w-12 h-12 object-contain"
                  />
                </div>
              <div>
                <h1 className="text-2xl font-bold text-white">
                  P&ID Digital Intelligence
                </h1>
                <p className="text-slate-400 text-sm">
                  Convert Process Diagrams to Structured Data
                </p>
              </div>
            </div>
            <div className="flex items-center space-x-4">
              <button
                onClick={openChat}
                className="px-4 py-2 bg-gradient-to-r from-yellow-400 to-yellow-500 hover:from-yellow-500 hover:to-yellow-600 text-black rounded-lg flex items-center space-x-2 transition-colors border-2 border-white font-bold"
              >
                <MessageCircle className="w-4 h-4" />
                <span>Ask APX CoPilot</span>
              </button>
              <button
                onClick={() => setShowUpload(false)}
                className="px-4 py-2 text-slate-400 hover:text-white transition-colors"
              >
                ← Back to Home
              </button>
            </div>
            </div>
          </div>
        </div>

        {/* Main Content */}
        <div className="max-w-7xl mx-auto px-6 py-8">
          <PIDUploadComponent />
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 p-6">
      <div className="bg-white/10 backdrop-blur-lg border border-white/20 rounded-2xl shadow-lg">
        {/* Header */}
        <div className="bg-slate-800/50 backdrop-blur-sm border-b border-slate-700 rounded-t-2xl">
          <div className="max-w-7xl mx-auto px-6 py-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-4">
                <div className="w-14 h-14 rounded-lg flex items-center justify-center">
                  <img
                    src="/logo.png"
                    alt="APX GP"
                    className="w-12 h-12 object-contain"
                  />
                </div>
                <div>
                  <h1 className="text-2xl font-bold text-white">
                    P&ID Digital Intelligence
                  </h1>
                  <p className="text-slate-400 text-sm">
                    Convert Process Diagrams to Structured Data
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Hero Section */}
        <div className="max-w-7xl mx-auto px-6 py-16">
          <div className="text-center mb-16">
            <h1 className="text-5xl font-bold text-white mb-6 leading-tight">
              Transform P&IDs into
              <span className="bg-gradient-to-r from-blue-400 to-cyan-300 bg-clip-text text-transparent">
                {" "}
                Digital Intelligence
              </span>
            </h1>
            <p className="text-xl text-slate-400 max-w-3xl mx-auto mb-12 leading-relaxed">
              Upload your Process & Instrumentation Diagrams and let our
              advanced AI extract components, connections, and metadata
              automatically. Convert legacy drawings into structured, searchable
              data in minutes.
            </p>

            <button
              onClick={() => setShowUpload(true)}
              className="group bg-gradient-to-r from-blue-600 to-cyan-500 hover:from-blue-700 hover:to-cyan-600 text-white px-10 py-5 rounded-xl font-bold text-xl transition-all duration-500 transform hover:scale-105 shadow-xl shadow-blue-500/25 hover:shadow-cyan-500/40"
            >
              <span className="relative z-10">
                Ignite the Engine
                <ArrowRight className="inline-block ml-3 w-6 h-6 group-hover:translate-x-2 transition-transform duration-300" />
              </span>
            </button>
          </div>

          {/* Features Grid */}
          <div className="grid md:grid-cols-3 gap-8 mb-20">
            <div className="group bg-slate-800/50 rounded-2xl p-8 border border-slate-700 hover:border-blue-500/50 transition-all duration-500 transform hover:scale-105 hover:shadow-lg hover:shadow-blue-500/20">
              <div className="w-14 h-14 bg-gradient-to-r from-blue-500 to-cyan-400 rounded-xl flex items-center justify-center mb-6">
                <FileImage className="w-7 h-7 text-white" />
              </div>
              <h3 className="text-2xl font-bold text-white mb-4">
                Smart Document Processing
              </h3>
              <p className="text-slate-400">
                Computer vision analyzes your P&ID drawings to identify
                equipment, instruments, and process flows with high accuracy.
              </p>
            </div>

            <div className="group bg-slate-800/50 rounded-2xl p-8 border border-slate-700 hover:border-blue-500/50 transition-all duration-500 transform hover:scale-105 hover:shadow-lg hover:shadow-blue-500/20">
              <div className="w-14 h-14 bg-gradient-to-r from-blue-500 to-cyan-400 rounded-xl flex items-center justify-center mb-6">
                <Brain className="w-7 h-7 text-white" />
              </div>
              <h3 className="text-2xl font-bold text-white mb-4">
                AI-Powered Recognition
              </h3>
              <p className="text-slate-400">
                Machine learning models automatically classify symbols, tags,
                and connections to deliver structured results.
              </p>
            </div>

            <div className="group bg-slate-800/50 rounded-2xl p-8 border border-slate-700 hover:border-blue-500/50 transition-all duration-500 transform hover:scale-105 hover:shadow-lg hover:shadow-blue-500/20">
              <div className="w-14 h-14 bg-gradient-to-r from-blue-500 to-cyan-400 rounded-xl flex items-center justify-center mb-6">
                <Database className="w-7 h-7 text-white" />
              </div>
              <h3 className="text-2xl font-bold text-white mb-4">
                Structured Data Export
              </h3>
              <p className="text-slate-400">
                Export results in multiple formats including JSON, XML, CSV, and
                industry-standard models for seamless integration.
              </p>
            </div>
          </div>

          {/* Benefits Section */}
          <div className="bg-slate-800/40 backdrop-blur-sm rounded-3xl p-12 border border-slate-700">
            <div className="text-center mb-12">
              <h2 className="text-4xl font-bold text-white mb-4">
                Why Choose P&ID Digital Intelligence?
              </h2>
              <p className="text-slate-400 text-lg max-w-3xl mx-auto">
                Improve accuracy, save time, and bring intelligence to your
                engineering workflows.
              </p>
            </div>

            <div className="grid md:grid-cols-2 gap-12">
              <div className="space-y-8">
                <div className="flex items-start space-x-4">
                  <CheckCircle className="w-6 h-6 text-blue-400 flex-shrink-0 mt-1" />
                  <div>
                    <h4 className="text-white font-bold mb-2 text-xl">
                      Save Time & Reduce Errors
                    </h4>
                    <p className="text-slate-400">
                      Automated extraction reduces manual effort and minimizes
                      errors.
                    </p>
                  </div>
                </div>

                <div className="flex items-start space-x-4">
                  <CheckCircle className="w-6 h-6 text-blue-400 flex-shrink-0 mt-1" />
                  <div>
                    <h4 className="text-white font-bold mb-2 text-xl">
                      Industry Standard Compliance
                    </h4>
                    <p className="text-slate-400">
                      Built on ISA and ANSI standards for consistent and
                      reliable recognition.
                    </p>
                  </div>
                </div>
              </div>

              <div className="space-y-8">
                <div className="flex items-start space-x-4">
                  <CheckCircle className="w-6 h-6 text-blue-400 flex-shrink-0 mt-1" />
                  <div>
                    <h4 className="text-white font-bold mb-2 text-xl">
                      Multiple Format Support
                    </h4>
                    <p className="text-slate-400">
                      Process PDF, PNG, JPEG, and other formats with high
                      accuracy.
                    </p>
                  </div>
                </div>

                <div className="flex items-start space-x-4">
                  <CheckCircle className="w-6 h-6 text-blue-400 flex-shrink-0 mt-1" />
                  <div>
                    <h4 className="text-white font-bold mb-2 text-xl">
                      Easy Integration
                    </h4>
                    <p className="text-slate-400">
                      REST API and webhook support to connect with your existing
                      systems.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Final CTA */}
          <div className="text-center mt-20">
            <h2 className="text-4xl font-bold text-white mb-6">
              Ready to Get Started?
            </h2>
            <p className="text-lg text-slate-400 mb-10 max-w-2xl mx-auto">
              Join engineering teams transforming their process documentation
              with AI.
            </p>

            <button
              onClick={() => setShowUpload(true)}
              className="group bg-gradient-to-r from-blue-600 to-cyan-500 hover:from-blue-700 hover:to-cyan-600 text-white px-12 py-6 rounded-xl font-bold text-2xl transition-all duration-500 transform hover:scale-105 shadow-xl shadow-blue-500/25 hover:shadow-cyan-500/40"
            >
              <span className="relative z-10">
                Get Started Now
                <ArrowRight className="inline-block ml-4 w-7 h-7 group-hover:translate-x-2 transition-transform duration-300" />
              </span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Index;
