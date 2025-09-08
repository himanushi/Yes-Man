/**
 * Yes-Man 顔アニメーションコンポーネント
 * 
 * Fallout New Vegas風の顔表示とアニメーション
 * 憲法V: パフォーマンス制約 - スムーズなアニメーション
 */

import React, { useEffect, useState, useCallback, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  FaceState, 
  FaceExpression, 
  AnimationState, 
  FaceAnimationProps 
} from '../types';
import './FaceAnimation.css';

const FaceAnimation: React.FC<FaceAnimationProps> = ({
  state,
  expression,
  animationState,
  className = '',
  size = 300,
  onStateChange
}) => {
  // アニメーション制御
  const [currentFrame, setCurrentFrame] = useState(0);
  const [isAnimating, setIsAnimating] = useState(false);

  // 状態に応じた色設定
  const stateColors = useMemo(() => ({
    idle: {
      primary: '#00ff41',      // Matrix緑
      secondary: '#008f11',
      glow: '#00ff4155',
      background: '#001100'
    },
    listening: {
      primary: '#41ff00',      // 明るい緑（音声認識中）
      secondary: '#11aa00',
      glow: '#41ff0088',
      background: '#002200'
    },
    thinking: {
      primary: '#ffaa00',      // オレンジ（思考中）
      secondary: '#cc6600',
      glow: '#ffaa0066',
      background: '#221100'
    },
    speaking: {
      primary: '#0099ff',      // 青（発話中）
      secondary: '#0066cc',
      glow: '#0099ff88',
      background: '#001122'
    },
    error: {
      primary: '#ff0000',      // 赤（エラー）
      secondary: '#cc0000',
      glow: '#ff000088',
      background: '#220000'
    },
    sleeping: {
      primary: '#666666',      // グレー（スリープ）
      secondary: '#333333',
      glow: '#66666644',
      background: '#111111'
    }
  }), []);

  const currentColors = stateColors[state];

  // 表情に応じた形状調整
  const expressionShapes = useMemo(() => ({
    neutral: {
      eyeScale: 1.0,
      eyeRotation: 0,
      mouthCurve: 0,
      eyebrowPosition: 0
    },
    happy: {
      eyeScale: 0.8,
      eyeRotation: -5,
      mouthCurve: 0.3,
      eyebrowPosition: -5
    },
    excited: {
      eyeScale: 1.2,
      eyeRotation: 0,
      mouthCurve: 0.5,
      eyebrowPosition: -10
    },
    confused: {
      eyeScale: 1.1,
      eyeRotation: 3,
      mouthCurve: -0.1,
      eyebrowPosition: 5
    },
    sad: {
      eyeScale: 0.9,
      eyeRotation: 8,
      mouthCurve: -0.3,
      eyebrowPosition: 10
    },
    angry: {
      eyeScale: 0.7,
      eyeRotation: -10,
      mouthCurve: -0.2,
      eyebrowPosition: 15
    },
    surprised: {
      eyeScale: 1.4,
      eyeRotation: 0,
      mouthCurve: 0,
      eyebrowPosition: -15
    }
  }), []);

  const currentExpression = expressionShapes[expression];

  // 瞬きアニメーション
  const handleBlink = useCallback(() => {
    if (animationState.eyeBlinkRate > 0) {
      setIsAnimating(true);
      setTimeout(() => setIsAnimating(false), 150);
    }
  }, [animationState.eyeBlinkRate]);

  // 定期的な瞬き
  useEffect(() => {
    if (animationState.eyeBlinkRate > 0) {
      const blinkInterval = 2000 + Math.random() * 3000; // 2-5秒間隔
      const timer = setInterval(handleBlink, blinkInterval);
      return () => clearInterval(timer);
    }
  }, [animationState.eyeBlinkRate, handleBlink]);

  // パルスアニメーション
  useEffect(() => {
    if (animationState.pulseSpeed > 0) {
      const pulseInterval = setInterval(() => {
        setCurrentFrame(prev => (prev + 1) % 60);
      }, 1000 / (animationState.pulseSpeed * 30)); // 30fps基準
      
      return () => clearInterval(pulseInterval);
    }
  }, [animationState.pulseSpeed]);

  // 状態変更通知
  useEffect(() => {
    onStateChange?.(state);
  }, [state, onStateChange]);

  // Yes-Manスタイルの顔描画
  const renderFace = () => {
    const centerX = size / 2;
    const centerY = size / 2;
    const faceRadius = size * 0.4;
    
    // パルス効果
    const pulseScale = 1 + Math.sin(currentFrame * 0.3) * animationState.glowIntensity * 0.1;
    
    return (
      <motion.svg
        width={size}
        height={size}
        viewBox={`0 0 ${size} ${size}`}
        className="face-svg"
        animate={{
          scale: pulseScale,
          rotate: animationState.headTilt * 10
        }}
        transition={{
          duration: 0.3,
          ease: "easeInOut"
        }}
      >
        {/* 背景グロー */}
        <defs>
          <radialGradient id="glowGradient" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor={currentColors.glow} />
            <stop offset="100%" stopColor="transparent" />
          </radialGradient>
          <filter id="glow">
            <feGaussianBlur stdDeviation="3" result="coloredBlur"/>
            <feMerge>
              <feMergeNode in="coloredBlur"/>
              <feMergeNode in="SourceGraphic"/>
            </feMerge>
          </filter>
        </defs>

        {/* 外側グロー */}
        <circle
          cx={centerX}
          cy={centerY}
          r={faceRadius * 1.3}
          fill="url(#glowGradient)"
          opacity={animationState.glowIntensity}
        />

        {/* 顔の輪郭 */}
        <circle
          cx={centerX}
          cy={centerY}
          r={faceRadius}
          fill={currentColors.background}
          stroke={currentColors.primary}
          strokeWidth="3"
          filter="url(#glow)"
        />

        {/* 左目 */}
        <motion.ellipse
          cx={centerX - faceRadius * 0.3}
          cy={centerY - faceRadius * 0.2}
          rx={faceRadius * 0.15 * currentExpression.eyeScale}
          ry={isAnimating ? 2 : faceRadius * 0.08 * animationState.eyeOpenness}
          fill={currentColors.primary}
          animate={{
            rotate: currentExpression.eyeRotation,
            opacity: state === 'sleeping' ? 0.3 : 1
          }}
          transition={{ duration: 0.2 }}
        />

        {/* 右目 */}
        <motion.ellipse
          cx={centerX + faceRadius * 0.3}
          cy={centerY - faceRadius * 0.2}
          rx={faceRadius * 0.15 * currentExpression.eyeScale}
          ry={isAnimating ? 2 : faceRadius * 0.08 * animationState.eyeOpenness}
          fill={currentColors.primary}
          animate={{
            rotate: currentExpression.eyeRotation,
            opacity: state === 'sleeping' ? 0.3 : 1
          }}
          transition={{ duration: 0.2 }}
        />

        {/* 眉毛（左） */}
        <motion.rect
          x={centerX - faceRadius * 0.4}
          y={centerY - faceRadius * 0.4}
          width={faceRadius * 0.2}
          height="3"
          rx="1"
          fill={currentColors.secondary}
          animate={{
            y: centerY - faceRadius * 0.4 + currentExpression.eyebrowPosition,
            rotate: currentExpression.eyeRotation * 0.5
          }}
          transition={{ duration: 0.3 }}
        />

        {/* 眉毛（右） */}
        <motion.rect
          x={centerX + faceRadius * 0.2}
          y={centerY - faceRadius * 0.4}
          width={faceRadius * 0.2}
          height="3"
          rx="1"
          fill={currentColors.secondary}
          animate={{
            y: centerY - faceRadius * 0.4 + currentExpression.eyebrowPosition,
            rotate: -currentExpression.eyeRotation * 0.5
          }}
          transition={{ duration: 0.3 }}
        />

        {/* 口 */}
        <motion.path
          d={`M ${centerX - faceRadius * 0.2} ${centerY + faceRadius * 0.2} 
              Q ${centerX} ${centerY + faceRadius * 0.2 - currentExpression.mouthCurve * 20} 
                ${centerX + faceRadius * 0.2} ${centerY + faceRadius * 0.2}`}
          fill="none"
          stroke={currentColors.primary}
          strokeWidth="4"
          strokeLinecap="round"
          animate={{
            pathLength: animationState.mouthMovement,
            opacity: state === 'speaking' ? 0.8 + Math.sin(currentFrame * 0.8) * 0.2 : 1
          }}
          transition={{ duration: 0.1 }}
        />

        {/* 音声波形表示（speaking状態時） */}
        <AnimatePresence>
          {state === 'speaking' && (
            <g>
              {[...Array(5)].map((_, i) => (
                <motion.line
                  key={i}
                  x1={centerX - faceRadius * 0.1 + i * 10}
                  y1={centerY + faceRadius * 0.5}
                  x2={centerX - faceRadius * 0.1 + i * 10}
                  y2={centerY + faceRadius * 0.5 - Math.sin(currentFrame * 0.5 + i) * 20}
                  stroke={currentColors.primary}
                  strokeWidth="2"
                  strokeLinecap="round"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                />
              ))}
            </g>
          )}
        </AnimatePresence>

        {/* リスニングインジケータ（listening状態時） */}
        <AnimatePresence>
          {state === 'listening' && (
            <g>
              {[...Array(3)].map((_, i) => (
                <motion.circle
                  key={i}
                  cx={centerX}
                  cy={centerY}
                  r={faceRadius * (0.6 + i * 0.2)}
                  fill="none"
                  stroke={currentColors.primary}
                  strokeWidth="1"
                  opacity={0.3}
                  initial={{ scale: 0 }}
                  animate={{ scale: [0, 1, 0] }}
                  transition={{
                    duration: 2,
                    repeat: Infinity,
                    delay: i * 0.3
                  }}
                />
              ))}
            </g>
          )}
        </AnimatePresence>
      </motion.svg>
    );
  };

  // 状態テキスト表示
  const getStateText = () => {
    const stateTexts = {
      idle: 'はい！何でもお聞きください！',
      listening: '聞いています...',
      thinking: '考え中です...',
      speaking: 'お答えしています',
      error: 'エラーが発生しました',
      sleeping: 'スリープ中'
    };
    return stateTexts[state];
  };

  return (
    <div className={`face-animation ${className} face-state-${state}`}>
      <motion.div 
        className="face-container"
        initial={{ opacity: 0, scale: 0.8 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.5 }}
      >
        {renderFace()}
        
        {/* 状態テキスト */}
        <motion.div 
          className="state-text"
          key={state} // 状態変更時に再アニメーション
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
          style={{ color: currentColors.primary }}
        >
          {getStateText()}
        </motion.div>

        {/* デバッグ情報（開発時のみ） */}
        {process.env.NODE_ENV === 'development' && (
          <div className="debug-info">
            <div>State: {state}</div>
            <div>Expression: {expression}</div>
            <div>Blink Rate: {animationState.eyeBlinkRate.toFixed(2)}</div>
            <div>Eye Openness: {animationState.eyeOpenness.toFixed(2)}</div>
            <div>Mouth Movement: {animationState.mouthMovement.toFixed(2)}</div>
            <div>Glow Intensity: {animationState.glowIntensity.toFixed(2)}</div>
          </div>
        )}
      </motion.div>
    </div>
  );
};

export default FaceAnimation;