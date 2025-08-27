import { useState, useEffect } from 'react';

const RetroTitle = () => {
  const [glitchText, setGlitchText] = useState('SOLEFLIP');
  const originalText = 'SOLEFLIP';
  const glitchChars = '!<>-_\\/[]{}—=+*^?#________';

  useEffect(() => {
    const glitchInterval = setInterval(() => {
      if (Math.random() < 0.1) { // 10% chance to glitch
        const glitched = originalText
          .split('')
          .map(char => 
            Math.random() < 0.3 
              ? glitchChars[Math.floor(Math.random() * glitchChars.length)]
              : char
          )
          .join('');
        
        setGlitchText(glitched);
        
        // Restore original text after short delay
        setTimeout(() => setGlitchText(originalText), 100);
      }
    }, 2000);

    return () => clearInterval(glitchInterval);
  }, []);

  return (
    <div className="text-center">
      <div className="ascii-art text-retro-cyan animate-glow">
        {`╔═══════════════════════╗
║                       ║
║      S O L E F L I P  ║
║                       ║
╚═══════════════════════╝`}
      </div>
      <div className="mt-2">
        <h1 className="font-retro text-2xl font-bold text-retro-magenta animate-flicker">
          {glitchText}
        </h1>
        <p className="text-xs text-retro-cyan/70 uppercase tracking-widest mt-1">
          Admin Control Panel
        </p>
      </div>
    </div>
  );
};

export default RetroTitle;