import appConfig from '../../config/app.config.json';
import styleConfig from '../../config/style.config.json';
import type { AppConfig, StyleConfig } from '../types';

export const APP_CONFIG = appConfig as AppConfig;
export const STYLE_CONFIG = styleConfig as StyleConfig;
export const INDONESIA_BOUNDS = APP_CONFIG.indonesiaBounds;
export const MAP_DEFAULTS = APP_CONFIG.mapDefaults;
export const BASEMAPS = APP_CONFIG.basemaps;
export const DEFAULT_DATE = APP_CONFIG.defaultDate;
export const DEFAULT_OPACITY = APP_CONFIG.defaultOpacity;
export const STALE_AFTER_HOURS = APP_CONFIG.staleAfterHours;
