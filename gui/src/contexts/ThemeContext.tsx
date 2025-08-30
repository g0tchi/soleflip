import React, { createContext, useContext, useState, useEffect } from 'react';

export type ThemeType = 'retro-cyan' | 'retro-green' | 'retro-magenta' | 'retro-yellow' | 'claude-code' | 'purple-haze' | 'happy-hues-modern';

interface ThemeContextType {
  theme: ThemeType;
  setTheme: (theme: ThemeType) => void;
  getThemeClasses: () => string;
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

export const useTheme = () => {
  const context = useContext(ThemeContext);
  if (context === undefined) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }
  return context;
};

interface ThemeProviderProps {
  children: React.ReactNode;
}

export const ThemeProvider: React.FC<ThemeProviderProps> = ({ children }) => {
  const [theme, setThemeState] = useState<ThemeType>('happy-hues-modern');

  useEffect(() => {
    // Stabilize theme loading to prevent disappearing display
    const savedTheme = localStorage.getItem('soleflip-theme') as ThemeType;
    const validThemes: ThemeType[] = ['retro-cyan', 'retro-green', 'retro-magenta', 'retro-yellow', 'claude-code', 'purple-haze', 'happy-hues-modern'];
    
    let themeToApply: ThemeType = 'happy-hues-modern'; // default
    
    if (savedTheme && validThemes.includes(savedTheme)) {
      themeToApply = savedTheme;
    } else {
      localStorage.setItem('soleflip-theme', 'happy-hues-modern');
    }
    
    // Apply theme immediately and consistently
    setThemeState(themeToApply);
    document.documentElement.className = `theme-${themeToApply}`;
    
    // Ensure body has consistent styling
    document.body.style.margin = '0';
    document.body.style.padding = '0';
    document.body.style.minHeight = '100vh';
  }, []);

  const setTheme = (newTheme: ThemeType) => {
    setThemeState(newTheme);
    localStorage.setItem('soleflip-theme', newTheme);
    
    // Apply theme to document root
    document.documentElement.className = `theme-${newTheme}`;
  };

  const getThemeClasses = () => {
    switch (theme) {
      case 'retro-cyan':
        return 'theme-retro-cyan';
      case 'retro-green':
        return 'theme-retro-green';  
      case 'retro-magenta':
        return 'theme-retro-magenta';
      case 'retro-yellow':
        return 'theme-retro-yellow';
      case 'claude-code':
        return 'theme-claude-code';
      case 'purple-haze':
        return 'theme-purple-haze';
      case 'happy-hues-modern':
        return 'theme-happy-hues-modern';
      default:
        return 'theme-happy-hues-modern';
    }
  };


  const value: ThemeContextType = {
    theme,
    setTheme,
    getThemeClasses
  };

  return (
    <ThemeContext.Provider value={value}>
      {children}
    </ThemeContext.Provider>
  );
};