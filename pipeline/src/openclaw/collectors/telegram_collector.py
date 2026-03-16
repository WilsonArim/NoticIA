"""Telegram Channel Collector — 1278 channels via Telethon."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from openclaw.collectors.base import BaseCollector
from openclaw.config import TELEGRAM_API_ID, TELEGRAM_API_HASH
from openclaw.models import RawEvent

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Channels with credibility metadata
# tier: 1 = official gov/agency  |  2 = major media
#        3 = established independent  |  4 = OSINT aggregator
#        5 = partisan but fast (needs cross-check)
# bias: editorial lean (for fact-check weighting, NOT filtering)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TELEGRAM_CHANNELS: list[dict] = [

    # ══════════════════════════════════════════════════════════════════
    #  BREAKING NEWS / MAJOR MEDIA  (tier 1-2)
    # ══════════════════════════════════════════════════════════════════
    {"handle": "bbcnews", "tier": 2, "bias": "uk-centric", "area": "general"},
    {"handle": "reuters", "tier": 1, "bias": "none", "area": "general"},
    {"handle": "AJEnglish", "tier": 2, "bias": "qatar-aligned", "area": "general"},
    {"handle": "guardian", "tier": 2, "bias": "centre-left", "area": "general"},
    {"handle": "ap", "tier": 1, "bias": "none", "area": "general"},
    {"handle": "france24_en", "tier": 2, "bias": "france-centric", "area": "general"},
    {"handle": "financialtimes", "tier": 2, "bias": "none", "area": "general"},
    {"handle": "nytimes", "tier": 2, "bias": "centre-left", "area": "general"},
    {"handle": "StraightsTimes", "tier": 2, "bias": "singapore-centric", "area": "general"},
    {"handle": "disclosetv", "tier": 3, "bias": "none", "area": "general"},  # 350k
    {"handle": "Mothership_sg", "tier": 3, "bias": "singapore-centric", "area": "general"},
    {"handle": "rt_breaking", "tier": 4, "bias": "pro-russia", "area": "general"},
    {"handle": "tass_agency", "tier": 2, "bias": "pro-russia", "area": "general"},
    {"handle": "insider", "tier": 2, "bias": "us-centric", "area": "general"},
    {"handle": "dwnews", "tier": 2, "bias": "germany-centric", "area": "general"},  # Deutsche Welle
    {"handle": "euronews", "tier": 2, "bias": "eu-centric", "area": "general"},  # Euronews
    {"handle": "SkyNewsBreak", "tier": 2, "bias": "uk-centric", "area": "general"},
    {"handle": "TheEconomist", "tier": 2, "bias": "liberal-centrist", "area": "general"},
    {"handle": "washingtonpost", "tier": 2, "bias": "centre-left", "area": "general"},
    {"handle": "anadoluagency", "tier": 2, "bias": "turkey-centric", "area": "general"},  # Anadolu Agency
    {"handle": "SCMPNews", "tier": 2, "bias": "hk-centric", "area": "general"},  # South China Morning Post
    {"handle": "BRICSinfo", "tier": 3, "bias": "multipolar", "area": "general"},  # 137k
    {"handle": "InsiderPaper", "tier": 3, "bias": "none", "area": "general"},  # 113k fast alerts

    # ══════════════════════════════════════════════════════════════════
    #  WAR / CONFLICT — LIVE COMBAT & BATTLEFIELD
    # ══════════════════════════════════════════════════════════════════
    {"handle": "ClashReport", "tier": 3, "bias": "none", "area": "defense"},
    {"handle": "AMK_Mapping", "tier": 3, "bias": "none", "area": "defense"},
    {"handle": "militarysummary", "tier": 3, "bias": "slightly-pro-russia", "area": "defense"},
    {"handle": "intelslava", "tier": 5, "bias": "pro-russia", "area": "defense"},
    {"handle": "southfronteng", "tier": 4, "bias": "pro-russia", "area": "defense"},
    {"handle": "liveconflictmaps", "tier": 3, "bias": "none", "area": "defense"},
    {"handle": "ourwarstoday", "tier": 3, "bias": "none", "area": "defense"},
    {"handle": "warmonitors", "tier": 4, "bias": "none", "area": "defense"},  # 160k
    {"handle": "war_monitor", "tier": 4, "bias": "none", "area": "defense"},
    {"handle": "militarywave", "tier": 4, "bias": "none", "area": "defense"},
    {"handle": "QJ6JJ", "tier": 4, "bias": "none", "area": "defense"},  # Military Waves
    {"handle": "WW3INFO", "tier": 5, "bias": "alarmist", "area": "defense"},
    {"handle": "BellumActaNews", "tier": 4, "bias": "right-leaning", "area": "defense"},
    {"handle": "MilitaryNewsEN", "tier": 3, "bias": "none", "area": "defense"},
    {"handle": "GeneralMCNews", "tier": 4, "bias": "us-right", "area": "defense"},
    {"handle": "WarNoir", "tier": 3, "bias": "none", "area": "defense"},  # 52k
    {"handle": "warandtactic", "tier": 4, "bias": "none", "area": "defense"},
    {"handle": "frontier_conflict", "tier": 4, "bias": "none", "area": "defense"},
    {"handle": "MissilesNukes", "tier": 4, "bias": "none", "area": "defense"},
    {"handle": "MilitaryLand", "tier": 3, "bias": "none", "area": "defense"},  # military.land
    {"handle": "WarArchive", "tier": 4, "bias": "none", "area": "defense"},
    {"handle": "ArmedConflicts", "tier": 3, "bias": "none", "area": "defense"},

    # ══════════════════════════════════════════════════════════════════
    #  UKRAINE / RUSSIA CONFLICT
    # ══════════════════════════════════════════════════════════════════
    {"handle": "rybar", "tier": 4, "bias": "pro-russia", "area": "defense"},
    {"handle": "ukrainenow", "tier": 3, "bias": "pro-ukraine", "area": "defense"},
    {"handle": "nexta_live", "tier": 3, "bias": "pro-opposition", "area": "defense"},
    {"handle": "ukraine_watch", "tier": 3, "bias": "pro-ukraine", "area": "defense"},  # 69k
    {"handle": "GeneralStaffZSU", "tier": 1, "bias": "pro-ukraine", "area": "defense"},
    {"handle": "operativnoZSU", "tier": 2, "bias": "pro-ukraine", "area": "defense"},
    {"handle": "Tsaplienko", "tier": 3, "bias": "pro-ukraine", "area": "defense"},
    {"handle": "bazabazon", "tier": 4, "bias": "pro-russia", "area": "defense"},
    {"handle": "Deep_State_UA", "tier": 3, "bias": "pro-ukraine", "area": "defense"},
    {"handle": "russian_losses", "tier": 3, "bias": "pro-ukraine", "area": "defense"},
    {"handle": "MoD_Russia", "tier": 1, "bias": "pro-russia", "area": "defense"},  # 99.8k
    {"handle": "WarTranslated", "tier": 3, "bias": "pro-ukraine", "area": "defense"},  # 16k
    {"handle": "DenysDavydov", "tier": 3, "bias": "pro-ukraine", "area": "defense"},  # 232k
    {"handle": "CombatFootageUA", "tier": 4, "bias": "pro-ukraine", "area": "defense"},  # 90k
    {"handle": "Suriyakmaps", "tier": 3, "bias": "none", "area": "defense"},  # 45k
    {"handle": "KyivIndependent", "tier": 2, "bias": "pro-ukraine", "area": "defense"},
    {"handle": "meduzaproject", "tier": 3, "bias": "independent-russia", "area": "intl_politics"},  # Meduza
    {"handle": "mediazona", "tier": 3, "bias": "independent-russia", "area": "intl_politics"},  # Mediazona
    {"handle": "UkraineWorld", "tier": 3, "bias": "pro-ukraine", "area": "defense"},
    {"handle": "SBUkr", "tier": 1, "bias": "pro-ukraine", "area": "defense"},  # SBU official

    # ══════════════════════════════════════════════════════════════════
    #  MIDDLE EAST CONFLICTS
    # ══════════════════════════════════════════════════════════════════
    {"handle": "middleeastspectator", "tier": 3, "bias": "pro-palestine", "area": "defense"},
    {"handle": "middleeastobserver", "tier": 3, "bias": "balanced-me", "area": "defense"},
    {"handle": "QudsNen", "tier": 4, "bias": "pro-palestine", "area": "defense"},
    {"handle": "idfofficial", "tier": 1, "bias": "pro-israel", "area": "defense"},  # 173k
    {"handle": "iran_intl", "tier": 3, "bias": "anti-regime-iran", "area": "geopolitics"},
    {"handle": "PressTV", "tier": 4, "bias": "pro-iran", "area": "geopolitics"},
    {"handle": "yemen_rw", "tier": 4, "bias": "neutral-monitoring", "area": "defense"},
    {"handle": "geopolitics_prime", "tier": 4, "bias": "none", "area": "defense"},  # 286k
    {"handle": "Israel_Iran_war_news", "tier": 4, "bias": "none", "area": "defense"},
    {"handle": "IsraelWarLive", "tier": 4, "bias": "none", "area": "defense"},  # 31k
    {"handle": "GazaNowEn", "tier": 4, "bias": "pro-palestine", "area": "defense"},  # 196k
    {"handle": "IranMilitary", "tier": 4, "bias": "pro-iran", "area": "defense"},  # 56k
    {"handle": "YemenMilitary", "tier": 4, "bias": "none", "area": "defense"},  # 14k
    {"handle": "i24news_EN", "tier": 2, "bias": "pro-israel", "area": "defense"},
    {"handle": "AlarabiyaEng", "tier": 2, "bias": "saudi-aligned", "area": "defense"},
    {"handle": "TRTWorld", "tier": 2, "bias": "turkey-centric", "area": "geopolitics"},

    # ══════════════════════════════════════════════════════════════════
    #  AFRICA CONFLICTS
    # ══════════════════════════════════════════════════════════════════
    {"handle": "AfricaWars", "tier": 4, "bias": "neutral-monitoring", "area": "defense"},
    {"handle": "globalconflictmonitor", "tier": 3, "bias": "none", "area": "defense"},
    {"handle": "africaintel", "tier": 3, "bias": "none", "area": "defense"},
    {"handle": "RSFSudan", "tier": 5, "bias": "rsf-aligned", "area": "defense"},
    {"handle": "FanaMediaCorp", "tier": 3, "bias": "ethiopia-state", "area": "defense"},
    {"handle": "SaharaReporters", "tier": 3, "bias": "none", "area": "intl_politics"},  # Nigeria
    {"handle": "africanews_en", "tier": 2, "bias": "none", "area": "intl_politics"},  # Africanews

    # ══════════════════════════════════════════════════════════════════
    #  LATIN AMERICA
    # ══════════════════════════════════════════════════════════════════
    {"handle": "guerrasygeo", "tier": 4, "bias": "none", "area": "defense"},
    {"handle": "LatAmDaily", "tier": 3, "bias": "none", "area": "intl_politics"},

    # ══════════════════════════════════════════════════════════════════
    #  ASIA-PACIFIC
    # ══════════════════════════════════════════════════════════════════
    {"handle": "dragonwatch", "tier": 4, "bias": "none", "area": "geopolitics"},
    {"handle": "indiageopolitics", "tier": 4, "bias": "india-centric", "area": "geopolitics"},
    {"handle": "NPNewsMM", "tier": 3, "bias": "none", "area": "intl_politics"},  # Myanmar 99k
    {"handle": "ChannelNewsAsia", "tier": 2, "bias": "singapore-centric", "area": "general"},
    {"handle": "NikkeiAsia", "tier": 2, "bias": "japan-centric", "area": "economy"},
    {"handle": "hindustantimes", "tier": 2, "bias": "india-centric", "area": "general"},

    # ══════════════════════════════════════════════════════════════════
    #  OFFICIAL GOVERNMENT / MILITARY
    # ══════════════════════════════════════════════════════════════════
    {"handle": "U_S_CENTCOM", "tier": 1, "bias": "us-official", "area": "defense"},
    {"handle": "MID_Russia", "tier": 1, "bias": "pro-russia", "area": "diplomacy"},
    {"handle": "NATO", "tier": 1, "bias": "pro-nato", "area": "diplomacy"},
    {"handle": "UNNews", "tier": 1, "bias": "none", "area": "diplomacy"},
    {"handle": "gov_sg", "tier": 1, "bias": "singapore-official", "area": "intl_politics"},  # 242k
    {"handle": "EUCouncil", "tier": 1, "bias": "eu-official", "area": "diplomacy"},
    {"handle": "WhiteHouse", "tier": 1, "bias": "us-official", "area": "diplomacy"},
    {"handle": "kremlin_ru", "tier": 1, "bias": "pro-russia", "area": "diplomacy"},  # Kremlin

    # ══════════════════════════════════════════════════════════════════
    #  OSINT AGGREGATORS
    # ══════════════════════════════════════════════════════════════════
    {"handle": "OsintTv", "tier": 4, "bias": "none", "area": "geopolitics"},
    {"handle": "osintdefender", "tier": 3, "bias": "none", "area": "geopolitics"},
    {"handle": "OSINTIndustries", "tier": 3, "bias": "none", "area": "geopolitics"},
    {"handle": "DDGeopolitics", "tier": 4, "bias": "none", "area": "geopolitics"},
    {"handle": "GeoPWatch", "tier": 4, "bias": "none", "area": "geopolitics"},
    {"handle": "geopolitics_live", "tier": 4, "bias": "none", "area": "geopolitics"},
    {"handle": "rnintel", "tier": 4, "bias": "nationalist", "area": "geopolitics"},
    {"handle": "Cen4infoRes", "tier": 2, "bias": "none", "area": "geopolitics"},
    {"handle": "IntelCrab", "tier": 3, "bias": "none", "area": "geopolitics"},
    {"handle": "inteldoge", "tier": 4, "bias": "none", "area": "geopolitics"},  # IntelDoge
    {"handle": "OSINT_Group", "tier": 4, "bias": "none", "area": "geopolitics"},

    # ══════════════════════════════════════════════════════════════════
    #  GEOPOLITICS & STRATEGY
    # ══════════════════════════════════════════════════════════════════
    {"handle": "eurasianist", "tier": 4, "bias": "multipolar-ideology", "area": "geopolitics"},
    {"handle": "stratforintel", "tier": 3, "bias": "us-aligned", "area": "geopolitics"},
    {"handle": "GrandmastersGeo", "tier": 3, "bias": "none", "area": "geopolitics"},  # 67k
    {"handle": "ScottRitter", "tier": 4, "bias": "pro-russia", "area": "geopolitics"},  # 90k
    {"handle": "ForeignAffairsMag", "tier": 2, "bias": "us-establishment", "area": "geopolitics"},
    {"handle": "cfr_org", "tier": 2, "bias": "us-establishment", "area": "geopolitics"},  # Council on Foreign Relations

    # ══════════════════════════════════════════════════════════════════
    #  INTERNATIONAL POLITICS
    # ══════════════════════════════════════════════════════════════════
    {"handle": "JulianAssange", "tier": 3, "bias": "anti-establishment", "area": "intl_politics"},
    {"handle": "ITARMYofUkraine", "tier": 4, "bias": "pro-ukraine", "area": "intl_politics"},
    {"handle": "politico_eu", "tier": 2, "bias": "eu-centric", "area": "intl_politics"},
    {"handle": "INSIDERR_POLITIC", "tier": 4, "bias": "none", "area": "intl_politics"},  # 2.3M
    {"handle": "PalestineResist", "tier": 4, "bias": "pro-palestine", "area": "intl_politics"},  # 137k
    {"handle": "ZachXBT", "tier": 3, "bias": "none", "area": "disinfo"},  # blockchain investigator 94k
    {"handle": "FedRussianInsiders", "tier": 4, "bias": "anti-russia-govt", "area": "intl_politics"},  # 146k

    # ══════════════════════════════════════════════════════════════════
    #  FRENCH-LANGUAGE MILITARY
    # ══════════════════════════════════════════════════════════════════
    {"handle": "Opex360", "tier": 3, "bias": "france-centric", "area": "defense"},

    # ══════════════════════════════════════════════════════════════════
    #  ECONOMY & FINANCIAL MARKETS
    # ══════════════════════════════════════════════════════════════════
    {"handle": "bloombergfeeds", "tier": 2, "bias": "markets-first", "area": "economy"},
    {"handle": "forexlive_feed", "tier": 3, "bias": "none", "area": "financial_markets"},
    {"handle": "WatcherGuru", "tier": 3, "bias": "none", "area": "financial_markets"},  # 626k
    {"handle": "CryptoRankIO", "tier": 3, "bias": "none", "area": "financial_markets"},  # 845k
    {"handle": "zerohedge", "tier": 3, "bias": "contrarian", "area": "financial_markets"},  # ZeroHedge
    {"handle": "cnbc", "tier": 2, "bias": "us-markets", "area": "economy"},
    {"handle": "WSJmarkets", "tier": 2, "bias": "none", "area": "financial_markets"},
    {"handle": "tradingview", "tier": 3, "bias": "none", "area": "financial_markets"},  # 156k

    # ══════════════════════════════════════════════════════════════════
    #  CRYPTO & WEB3
    # ══════════════════════════════════════════════════════════════════
    {"handle": "whale_alert", "tier": 2, "bias": "none", "area": "crypto"},
    {"handle": "CoinDesk", "tier": 2, "bias": "none", "area": "crypto"},
    {"handle": "CoinMarketCapNews", "tier": 2, "bias": "none", "area": "crypto"},
    {"handle": "CoinPost", "tier": 3, "bias": "none", "area": "crypto"},  # 306k
    {"handle": "cointelegraph", "tier": 2, "bias": "none", "area": "crypto"},  # Cointelegraph
    {"handle": "theblock_", "tier": 2, "bias": "none", "area": "crypto"},  # The Block
    {"handle": "decryptmedia", "tier": 3, "bias": "none", "area": "crypto"},  # Decrypt Media
    {"handle": "CryptoRadarHQ", "tier": 3, "bias": "none", "area": "crypto"},  # 999k
    {"handle": "wublockchainenglish", "tier": 3, "bias": "none", "area": "crypto"},  # Wu Blockchain 321k
    {"handle": "BitcoinMagazine", "tier": 2, "bias": "btc-maximalist", "area": "crypto"},

    # ══════════════════════════════════════════════════════════════════
    #  TECH & CYBERSECURITY
    # ══════════════════════════════════════════════════════════════════
    {"handle": "TheHackersNews", "tier": 3, "bias": "none", "area": "tech"},
    {"handle": "ArsTechnica", "tier": 2, "bias": "none", "area": "tech"},
    {"handle": "topcybersecurity", "tier": 3, "bias": "none", "area": "tech"},
    {"handle": "AppleNewsFeed", "tier": 3, "bias": "none", "area": "tech"},  # 198k
    {"handle": "hacker_news_feed", "tier": 3, "bias": "none", "area": "tech"},
    {"handle": "githubtrending", "tier": 3, "bias": "none", "area": "tech"},
    {"handle": "perplexity", "tier": 3, "bias": "none", "area": "tech"},  # Discover Tech News 1.5M
    {"handle": "hiaimediaen", "tier": 3, "bias": "none", "area": "tech"},  # Hi AI Tech News 525k
    {"handle": "aipost", "tier": 3, "bias": "none", "area": "tech"},  # AI Post 932k
    {"handle": "BleepingComputerChannel", "tier": 3, "bias": "none", "area": "tech"},
    {"handle": "DEDSEClulz", "tier": 4, "bias": "none", "area": "tech"},  # DEDSEC cybersec 612k
    {"handle": "DarkReading", "tier": 3, "bias": "none", "area": "tech"},

    # ══════════════════════════════════════════════════════════════════
    #  ENERGY
    # ══════════════════════════════════════════════════════════════════
    {"handle": "OilPrice", "tier": 3, "bias": "none", "area": "energy"},
    {"handle": "EnergyIntel", "tier": 3, "bias": "none", "area": "energy"},

    # ══════════════════════════════════════════════════════════════════
    #  HEALTH & EPIDEMIOLOGY
    # ══════════════════════════════════════════════════════════════════
    {"handle": "epidscience", "tier": 3, "bias": "none", "area": "health"},
    {"handle": "WHO", "tier": 1, "bias": "none", "area": "health"},
    {"handle": "NewEnglandJournal", "tier": 1, "bias": "none", "area": "health"},

    # ══════════════════════════════════════════════════════════════════
    #  ENVIRONMENT & DISASTERS
    # ══════════════════════════════════════════════════════════════════
    {"handle": "Disaster_News", "tier": 3, "bias": "none", "area": "environment"},
    {"handle": "disasterfreaks", "tier": 4, "bias": "none", "area": "environment"},
    {"handle": "top_disasters", "tier": 4, "bias": "none", "area": "environment"},
    {"handle": "ClimateCrisisNow", "tier": 3, "bias": "climate-activist", "area": "environment"},
    {"handle": "EarthquakeWatch", "tier": 3, "bias": "none", "area": "environment"},

    # ══════════════════════════════════════════════════════════════════
    #  HUMAN RIGHTS
    # ══════════════════════════════════════════════════════════════════
    {"handle": "amnesty", "tier": 2, "bias": "none", "area": "human_rights"},
    {"handle": "hrw", "tier": 2, "bias": "none", "area": "human_rights"},
    {"handle": "RSF_inter", "tier": 2, "bias": "none", "area": "human_rights"},  # Reporters Without Borders
    {"handle": "ICCCourt", "tier": 1, "bias": "none", "area": "human_rights"},

    # ══════════════════════════════════════════════════════════════════
    #  DISINFO / FACT-CHECK
    # ══════════════════════════════════════════════════════════════════
    {"handle": "bellingcat", "tier": 2, "bias": "none", "area": "disinfo"},
    {"handle": "DFRLab", "tier": 2, "bias": "none", "area": "disinfo"},  # Atlantic Council DFRLab
    {"handle": "EUvsDisinfo", "tier": 2, "bias": "eu-aligned", "area": "disinfo"},

    # ══════════════════════════════════════════════════════════════════
    #  SCIENCE & SPACE
    # ══════════════════════════════════════════════════════════════════
    {"handle": "Nasa_News", "tier": 2, "bias": "none", "area": "science"},
    {"handle": "science", "tier": 3, "bias": "none", "area": "science"},
    {"handle": "nasa_apod", "tier": 2, "bias": "none", "area": "science"},
    {"handle": "NatureNews", "tier": 1, "bias": "none", "area": "science"},
    {"handle": "EverythingScience", "tier": 3, "bias": "none", "area": "science"},
    {"handle": "SpaceXChannel", "tier": 3, "bias": "none", "area": "science"},

    # ══════════════════════════════════════════════════════════════════
    #  SPORTS
    # ══════════════════════════════════════════════════════════════════
    {"handle": "allfootballss", "tier": 3, "bias": "none", "area": "sports"},
    {"handle": "transfer_news_football", "tier": 3, "bias": "none", "area": "sports"},
    {"handle": "Brfootball_en", "tier": 2, "bias": "none", "area": "sports"},
    {"handle": "PremierLeagueNews", "tier": 3, "bias": "none", "area": "sports"},  # 238k
    {"handle": "Sport_HUB_football", "tier": 3, "bias": "none", "area": "sports"},  # 1.9M
    {"handle": "sky_sports_football_updates", "tier": 2, "bias": "uk-centric", "area": "sports"},  # 262k
    {"handle": "Espn_Football_News_UK", "tier": 2, "bias": "us-centric", "area": "sports"},  # 99k
    {"handle": "Uefa_Champions_Leagueee", "tier": 3, "bias": "none", "area": "sports"},  # 165k
    {"handle": "onefootballclub_official", "tier": 3, "bias": "none", "area": "sports"},  # 98k
    {"handle": "br_football_news", "tier": 2, "bias": "none", "area": "sports"},  # B/R Football 80k
    {"handle": "sportsdirect_eng", "tier": 3, "bias": "none", "area": "sports"},  # 519k
    {"handle": "F1News_eng", "tier": 3, "bias": "none", "area": "sports"},
    {"handle": "UFCnewsEN", "tier": 3, "bias": "none", "area": "sports"},

    # ══════════════════════════════════════════════════════════════════
    #  PORTUGAL / CPLP / LUSOFONIA
    # ══════════════════════════════════════════════════════════════════
    {"handle": "portugalnoticias", "tier": 3, "bias": "none", "area": "portugal"},
    {"handle": "portugal_news", "tier": 3, "bias": "none", "area": "portugal"},
    {"handle": "SAPONoticias", "tier": 2, "bias": "none", "area": "portugal"},
    {"handle": "bbcbrasil", "tier": 2, "bias": "none", "area": "portugal"},
    {"handle": "observadorpt", "tier": 2, "bias": "centre-right", "area": "portugal"},  # Observador
    {"handle": "rtp_noticias", "tier": 1, "bias": "none", "area": "portugal"},  # RTP
    {"handle": "jornaldenoticias", "tier": 2, "bias": "none", "area": "portugal"},  # JN
    {"handle": "tsfradio", "tier": 2, "bias": "none", "area": "portugal"},  # TSF
    {"handle": "RicoBoletim", "tier": 3, "bias": "none", "area": "portugal"},  # Rico Boletim
    {"handle": "a11acom", "tier": 3, "bias": "none", "area": "portugal"},  # 11A.COM
    {"handle": "DanuzioNetoOSINT", "tier": 3, "bias": "none", "area": "portugal"},  # OSINT 135.8k
    {"handle": "JovemPanNews", "tier": 2, "bias": "centre-right", "area": "portugal"},  # 52.3k
    {"handle": "sputnikbrasil", "tier": 4, "bias": "pro-russia", "area": "portugal"},  # 74.7k
    {"handle": "RevistaOeste", "tier": 3, "bias": "right-leaning", "area": "portugal"},  # 35.7k
    {"handle": "cnnbrasil", "tier": 2, "bias": "centrist", "area": "portugal"},  # 40.2k
    {"handle": "g1portal", "tier": 2, "bias": "centrist", "area": "portugal"},  # Globo 14.3k
    {"handle": "Poder360oficial", "tier": 3, "bias": "none", "area": "portugal"},  # Poder360
    {"handle": "Metropoles_DF", "tier": 3, "bias": "none", "area": "portugal"},  # Metropoles
    {"handle": "gazetadopovo", "tier": 3, "bias": "centre-right", "area": "portugal"},  # Gazeta do Povo
    {"handle": "theinterceptbr", "tier": 3, "bias": "left-leaning", "area": "portugal"},  # The Intercept BR
    {"handle": "CentralGeopoliticaOSINT", "tier": 4, "bias": "none", "area": "portugal"},  # Geopolitica OSINT
    {"handle": "ucraniaagora", "tier": 4, "bias": "pro-ukraine", "area": "defense"},  # Ucrania AGORA PT
    {"handle": "operacionaispt", "tier": 3, "bias": "portugal-centric", "area": "portugal"},  # Operacionais.pt
    {"handle": "MidiaNINJA", "tier": 4, "bias": "left-activist", "area": "portugal"},  # Midia NINJA
    {"handle": "rtbrasil", "tier": 4, "bias": "pro-russia", "area": "portugal"},  # RT Brasil
    {"handle": "JornalGeopolitico", "tier": 3, "bias": "none", "area": "portugal"},  # Jornal Geopolitico

    # ==============================================================
    #  ARABIC-LANGUAGE
    # ==============================================================
    {"handle": "AjaNews", "tier": 2, "bias": "qatar-aligned", "area": "general"},  # AJ+ Arabic 1.4M
    {"handle": "gazaalannet", "tier": 4, "bias": "pro-palestine", "area": "defense"},  # Gaza Now AR 1.3M
    {"handle": "wars_news", "tier": 4, "bias": "none", "area": "defense"},  # Arabic war news 228k
    {"handle": "C_Military1", "tier": 4, "bias": "none", "area": "defense"},  # Arabic military 375k
    {"handle": "sepah_pasdaran", "tier": 3, "bias": "pro-iran", "area": "defense"},  # IRGC channel 505k
    {"handle": "sepah_news1", "tier": 4, "bias": "pro-iran", "area": "defense"},  # IRGC news 211k
    {"handle": "QODS_COM", "tier": 4, "bias": "pro-iran", "area": "defense"},  # Quds Force 311k
    {"handle": "jebhe_parsi", "tier": 4, "bias": "none", "area": "defense"},  # Persian front 192k
    {"handle": "Saberin_ir", "tier": 4, "bias": "pro-iran", "area": "intl_politics"},  # Iran insiders 751k
    {"handle": "IraninArabic", "tier": 3, "bias": "pro-iran", "area": "intl_politics"},  # Iran in Arabic 486k
    {"handle": "sepahcybery", "tier": 4, "bias": "pro-iran", "area": "intl_politics"},  # IRGC cyber 523k
    {"handle": "FO_RK", "tier": 3, "bias": "none", "area": "general"},  # Arabic news 5.6M
    {"handle": "khabarfouri", "tier": 3, "bias": "none", "area": "general"},  # Arabic instant news 5.4M
    {"handle": "ir_b0", "tier": 3, "bias": "none", "area": "general"},  # Arabic news 2.1M
    {"handle": "khabari", "tier": 3, "bias": "none", "area": "general"},  # Arabic news 1.8M
    {"handle": "akharinkhabar", "tier": 3, "bias": "none", "area": "general"},  # Latest news AR 1.8M

    # ==============================================================
    #  RUSSIAN-LANGUAGE
    # ==============================================================
    {"handle": "rian_ru", "tier": 2, "bias": "pro-russia", "area": "general"},  # RIA Novosti 3.2M
    {"handle": "novosti_efir", "tier": 3, "bias": "pro-russia", "area": "general"},  # Russian news 4.6M
    {"handle": "smi_rf_moskva", "tier": 3, "bias": "pro-russia", "area": "general"},  # Russian media 3.4M
    {"handle": "medvedev_telegram", "tier": 1, "bias": "pro-russia", "area": "intl_politics"},  # Medvedev official 1.8M
    {"handle": "RKadyrov_95", "tier": 1, "bias": "pro-russia", "area": "intl_politics"},  # Kadyrov official 2.1M
    {"handle": "SolovievLive", "tier": 4, "bias": "pro-russia", "area": "intl_politics"},  # Soloviev propagandist 1.2M
    {"handle": "vv_volodin", "tier": 1, "bias": "pro-russia", "area": "intl_politics"},  # Volodin Duma speaker 1.4M
    {"handle": "boris_rozhin", "tier": 3, "bias": "pro-russia", "area": "intl_politics"},  # Col Cassad 782k
    {"handle": "radarrussiia", "tier": 4, "bias": "pro-russia", "area": "defense"},  # Radar Russia 1.1M
    {"handle": "milinfolive", "tier": 3, "bias": "pro-russia", "area": "defense"},  # MilInfoLive 618k
    {"handle": "apwagner", "tier": 4, "bias": "pro-russia", "area": "defense"},  # Wagner group 316k
    {"handle": "hiaimedia", "tier": 3, "bias": "none", "area": "tech"},  # Hi AI Media RU 2.4M
    {"handle": "GPTMainNews", "tier": 3, "bias": "none", "area": "tech"},  # GPT/AI news RU 2.1M
    {"handle": "techmedia", "tier": 3, "bias": "none", "area": "tech"},  # Tech media RU 1.3M
    {"handle": "ASupersharij", "tier": 4, "bias": "pro-russia", "area": "intl_politics"},  # Sharij 1.5M
    {"handle": "obshina_ru", "tier": 4, "bias": "nationalist", "area": "intl_politics"},  # Community RU 628k
    {"handle": "xydessa", "tier": 3, "bias": "pro-russia", "area": "intl_politics"},  # Odessa 917k
    {"handle": "neuesausrussland", "tier": 3, "bias": "none", "area": "general"},  # News from Russia DE 169k
    {"handle": "RusBotschaft", "tier": 2, "bias": "pro-russia", "area": "defense"},  # Russian Embassy DE 21k
    {"handle": "russianmacro", "tier": 3, "bias": "none", "area": "defense"},  # Russian Macro 107k

    # ==============================================================
    #  UKRAINIAN-LANGUAGE
    # ==============================================================
    {"handle": "vanek_nikolaev", "tier": 3, "bias": "pro-ukraine", "area": "general"},  # Vanek Nikolaev 2.7M
    {"handle": "kievreal1", "tier": 3, "bias": "pro-ukraine", "area": "intl_politics"},  # Kiev Real 1.5M
    {"handle": "kievinfo_kyiv", "tier": 3, "bias": "pro-ukraine", "area": "general"},  # Kyiv info 1.1M
    {"handle": "ssternenko", "tier": 3, "bias": "pro-ukraine", "area": "general"},  # Sternenko activist 847k
    {"handle": "truexakyiv", "tier": 3, "bias": "pro-ukraine", "area": "general"},  # True Kyiv 839k
    {"handle": "kharkivlife", "tier": 3, "bias": "pro-ukraine", "area": "intl_politics"},  # Kharkiv Life 673k
    {"handle": "kpszsu", "tier": 2, "bias": "pro-ukraine", "area": "defense"},  # Armed Forces UA 873k
    {"handle": "DIUkraine", "tier": 2, "bias": "pro-ukraine", "area": "defense"},  # Defence Intel UA 232k
    {"handle": "PPOhlopci", "tier": 4, "bias": "pro-ukraine", "area": "defense"},  # Air defense UA 140k
    {"handle": "ukraine_pyx", "tier": 3, "bias": "pro-ukraine", "area": "defense"},  # Ukraine South 155k
    {"handle": "ppo_energy_poltava", "tier": 4, "bias": "pro-ukraine", "area": "defense"},  # Poltava air defense 133k
    {"handle": "molfar_global", "tier": 3, "bias": "none", "area": "tech"},  # Molfar OSINT 54k

    # ==============================================================
    #  SPANISH-LANGUAGE
    # ==============================================================
    {"handle": "rtnoticias", "tier": 3, "bias": "pro-russia", "area": "general"},  # RT Noticias ES 299k
    {"handle": "PatriaDigital", "tier": 3, "bias": "left-leaning", "area": "general"},  # Patria Digital 298k
    {"handle": "ElCallejon809podcast", "tier": 3, "bias": "none", "area": "general"},  # Dominican podcast 269k
    {"handle": "ZonaRojasubof", "tier": 4, "bias": "none", "area": "general"},  # Zona Roja 270k
    {"handle": "NoticiaUrgenteEcuador", "tier": 3, "bias": "none", "area": "general"},  # Ecuador news 209k
    {"handle": "ultimasnoticiasec", "tier": 3, "bias": "none", "area": "general"},  # Ecuador news 198k
    {"handle": "armapedia", "tier": 3, "bias": "none", "area": "general"},  # Armapedia 186k
    {"handle": "vitoquilestelegram", "tier": 3, "bias": "none", "area": "general"},  # Chile news 157k
    {"handle": "CHATRUTASDELCONFLICTO_ECUADOR", "tier": 4, "bias": "none", "area": "intl_politics"},  # Ecuador conflict 359k
    {"handle": "elOJOen", "tier": 3, "bias": "none", "area": "intl_politics"},  # El Ojo 188k
    {"handle": "laquintacolumna", "tier": 4, "bias": "conspiracy-leaning", "area": "intl_politics"},  # La 5ta Columna 176k
    {"handle": "wallstwolverine", "tier": 3, "bias": "none", "area": "intl_politics"},  # WallSt Wolverine ES 188k
    {"handle": "colombiaoscurarespaldo", "tier": 4, "bias": "none", "area": "intl_politics"},  # Colombia Oscura 187k
    {"handle": "NicolasMaduroMoros", "tier": 1, "bias": "left-authoritarian", "area": "intl_politics"},  # Maduro official 109k
    {"handle": "Patria_ve", "tier": 4, "bias": "chavista", "area": "intl_politics"},  # Venezuela Patria 154k
    {"handle": "denunciasantioqu", "tier": 4, "bias": "none", "area": "intl_politics"},  # Antioquia reports 145k
    {"handle": "RadarEconomicoVzla", "tier": 3, "bias": "none", "area": "economy"},  # Venezuela economy 164k
    {"handle": "formula1_racefans", "tier": 3, "bias": "none", "area": "sports"},  # F1 ES 122k
    {"handle": "infodefSPAIN", "tier": 3, "bias": "none", "area": "defense"},  # InfoDef Spain 30k
    {"handle": "geoestratego_oficial10", "tier": 3, "bias": "none", "area": "defense"},  # Geoestratego 61k
    {"handle": "Ars_belli", "tier": 3, "bias": "none", "area": "defense"},  # Ars Belli 40k
    {"handle": "PedroBanosBajos", "tier": 3, "bias": "none", "area": "defense"},  # Pedro Banos military 24k
    {"handle": "geoestratego_canals", "tier": 3, "bias": "none", "area": "defense"},  # Geoestratego channels 21k
    {"handle": "ferchtech", "tier": 3, "bias": "none", "area": "tech"},  # FerchTech ES 103k
    {"handle": "hiaimediaes", "tier": 3, "bias": "none", "area": "tech"},  # Hi AI Media ES 76k
    {"handle": "ramirezz_pablo", "tier": 3, "bias": "none", "area": "blog_analysis"},  # Pablo Ramirez blog 41k

    # ==============================================================
    #  FRENCH-LANGUAGE
    # ==============================================================
    {"handle": "France24_fr", "tier": 2, "bias": "france-centric", "area": "general"},  # France24 FR 53k
    {"handle": "Le_Journal_News", "tier": 3, "bias": "none", "area": "general"},  # Africa-France24 news 60k
    {"handle": "internationalreporters", "tier": 3, "bias": "none", "area": "general"},  # Intl reporters FR 59k
    {"handle": "ActuInternationale", "tier": 3, "bias": "none", "area": "general"},  # Actu Internationale 56k
    {"handle": "sputnik_afrique", "tier": 4, "bias": "pro-russia", "area": "general"},  # Sputnik Afrique 51k
    {"handle": "khazinml", "tier": 3, "bias": "none", "area": "general"},  # Khazin analysis 250k
    {"handle": "intelligence_economique", "tier": 3, "bias": "none", "area": "intl_politics"},  # FR economic intel 36k
    {"handle": "LeGrandReveil", "tier": 4, "bias": "right-leaning", "area": "intl_politics"},  # Le Grand Reveil 68k
    {"handle": "diplomaties", "tier": 3, "bias": "none", "area": "intl_politics"},  # Diplomaties FR 39k
    {"handle": "chroniques_des_conflits", "tier": 3, "bias": "none", "area": "intl_politics"},  # Conflict chronicles 33k
    {"handle": "russosphere", "tier": 3, "bias": "pro-russia", "area": "intl_politics"},  # Russosphere FR 46k
    {"handle": "InfosAes", "tier": 3, "bias": "none", "area": "intl_politics"},  # InfosAes FR 83k
    {"handle": "parolede", "tier": 3, "bias": "none", "area": "geopolitics"},  # Parole de FR geopolitics 35k
    {"handle": "LIONESS_VF", "tier": 3, "bias": "none", "area": "defense"},  # Lioness defense FR 37k
    {"handle": "calibrearmes", "tier": 3, "bias": "none", "area": "defense"},  # Calibre armes FR 36k
    {"handle": "strategie_militaire", "tier": 3, "bias": "none", "area": "defense"},  # Strategie militaire 23k
    {"handle": "drtechworld", "tier": 3, "bias": "none", "area": "tech"},  # Dr TechWorld FR 83k
    {"handle": "eurasianform", "tier": 3, "bias": "none", "area": "blog_analysis"},  # Eurasian Forum 25k
    {"handle": "infosportfootball3", "tier": 3, "bias": "none", "area": "sports"},  # FR football 89k

    # ==============================================================
    #  GERMAN-LANGUAGE
    # ==============================================================
    {"handle": "INSIDER_Nachrichten", "tier": 3, "bias": "none", "area": "general"},  # Insider News DE 1.4M
    {"handle": "auf1tv", "tier": 3, "bias": "right-leaning", "area": "general"},  # AUF1 TV 284k
    {"handle": "LIONMediaNews", "tier": 3, "bias": "right-leaning", "area": "general"},  # LION Media 141k
    {"handle": "reitschusterde", "tier": 3, "bias": "centre-right", "area": "general"},  # Reitschuster 219k
    {"handle": "FreieMedienTV", "tier": 3, "bias": "none", "area": "general"},  # Free Media TV DE 143k
    {"handle": "cumbertech", "tier": 3, "bias": "none", "area": "tech"},  # CumberTech DE 1.2M
    {"handle": "militaernews", "tier": 3, "bias": "none", "area": "defense"},  # Militar News DE 68k
    {"handle": "AntiSpiegel", "tier": 3, "bias": "pro-russia", "area": "intl_politics"},  # Anti-Spiegel 126k
    {"handle": "AliceWeidel_live", "tier": 1, "bias": "right-wing", "area": "intl_politics"},  # Alice Weidel AfD 118k
    {"handle": "Markuskrall_aa1", "tier": 3, "bias": "libertarian", "area": "intl_politics"},  # Markus Krall economy 306k
    {"handle": "StefanHomburgOffiziel", "tier": 3, "bias": "none", "area": "intl_politics"},  # Stefan Homburg 205k
    {"handle": "UnterBlogg", "tier": 3, "bias": "none", "area": "blog_analysis"},  # UnterBlog DE 61k
    {"handle": "rabbitresearch", "tier": 3, "bias": "none", "area": "education"},  # Rabbit Research DE 86k
    {"handle": "MPSCEconomics", "tier": 3, "bias": "none", "area": "education"},  # Economics education DE 62k
    {"handle": "Marodeutsch", "tier": 3, "bias": "none", "area": "business_innovation"},  # Maro Deutsch 64k
    {"handle": "flagman_de", "tier": 3, "bias": "none", "area": "business_innovation"},  # Flagman DE 45k

    # ==============================================================
    #  TURKISH-LANGUAGE
    # ==============================================================
    {"handle": "Daryo", "tier": 2, "bias": "none", "area": "general"},  # Daryo news 429k
    {"handle": "bpthaber", "tier": 3, "bias": "none", "area": "general"},  # BPT Haber 392k
    {"handle": "savashaberr", "tier": 3, "bias": "none", "area": "general"},  # Savas Haber war news 153k
    {"handle": "mhahabertg", "tier": 3, "bias": "none", "area": "general"},  # MHA Haber 152k
    {"handle": "asayisberkemaltr", "tier": 3, "bias": "none", "area": "general"},  # Asayis news 311k
    {"handle": "noyanbahadori", "tier": 3, "bias": "none", "area": "general"},  # Noyan Bahadori 219k
    {"handle": "solcugazete", "tier": 3, "bias": "left-leaning", "area": "intl_politics"},  # Solcu Gazete 355k
    {"handle": "RTErdogan", "tier": 1, "bias": "turkey-official", "area": "intl_politics"},  # Erdogan official 102k
    {"handle": "istihbarathaberiniz", "tier": 3, "bias": "none", "area": "intl_politics"},  # Intelligence news TR 62k
    {"handle": "ifsa_turk17", "tier": 4, "bias": "none", "area": "intl_politics"},  # Turkish politics 155k
    {"handle": "gundemturkiy", "tier": 3, "bias": "none", "area": "intl_politics"},  # Gundem Turkey 45k
    {"handle": "MyGovUz", "tier": 1, "bias": "uzbekistan-official", "area": "intl_politics"},  # Uzbekistan gov 268k
    {"handle": "dunyasavashbr", "tier": 3, "bias": "none", "area": "defense"},  # World Wars TR 151k
    {"handle": "tcdefense", "tier": 3, "bias": "none", "area": "defense"},  # TC Defense 89k
    {"handle": "ww3media", "tier": 3, "bias": "none", "area": "defense"},  # WW3 Media TR 107k
    {"handle": "MODiraq", "tier": 1, "bias": "iraq-official", "area": "defense"},  # Iraq MOD 168k
    {"handle": "askeriistihbarat", "tier": 3, "bias": "none", "area": "defense"},  # Military intel TR 76k
    {"handle": "herbixeber", "tier": 3, "bias": "none", "area": "defense"},  # Herbi Xeber 54k
    {"handle": "ayyildiztimresmi", "tier": 4, "bias": "nationalist", "area": "defense"},  # Ayyildiz Tim 28k
    {"handle": "harbiwinresmi", "tier": 3, "bias": "none", "area": "defense"},  # Harbi Win TR 27k
    {"handle": "cyber_102", "tier": 3, "bias": "none", "area": "tech"},  # Cyber 102 TR 101k
    {"handle": "rifitech", "tier": 3, "bias": "none", "area": "tech"},  # Rifi Tech TR 70k
    {"handle": "Kazansanaa", "tier": 3, "bias": "none", "area": "tech"},  # Kazan tech TR 67k
    {"handle": "janderebaw_media", "tier": 3, "bias": "none", "area": "business_innovation"},  # Business media TR 91k

    # ==============================================================
    #  PORTUGUESE / LUSOFONIA (expanded)
    # ==============================================================
    {"handle": "conflitoseguerrasoficial", "tier": 3, "bias": "none", "area": "defense"},  # Conflitos e Guerras PT 68k
    {"handle": "hojeno_mundomilitar", "tier": 3, "bias": "none", "area": "defense"},  # Mundo Militar PT 97k
    {"handle": "exercito_oficial", "tier": 2, "bias": "portugal-official", "area": "defense"},  # Exercito PT 35k
    {"handle": "brasilparalelooficial", "tier": 3, "bias": "right-leaning", "area": "intl_politics"},  # Brasil Paralelo 63k
    {"handle": "nikolasferreira", "tier": 1, "bias": "right-wing", "area": "intl_politics"},  # Nikolas Ferreira dep 219k
    {"handle": "bolsonarocarlos", "tier": 1, "bias": "right-wing", "area": "intl_politics"},  # Carlos Bolsonaro 123k
    {"handle": "jairbolsonarobrasil", "tier": 1, "bias": "right-wing", "area": "intl_politics"},  # Bolsonaro 1.2M
    {"handle": "senadorflaviobolsonaro", "tier": 1, "bias": "right-wing", "area": "intl_politics"},  # Flavio Bolsonaro 91k
    {"handle": "tsejus", "tier": 3, "bias": "none", "area": "intl_politics"},  # Tsejus PT 115k
    {"handle": "olegderipaska", "tier": 3, "bias": "pro-russia", "area": "intl_politics"},  # Deripaska PT 119k
    {"handle": "mirarendavariavel", "tier": 3, "bias": "none", "area": "economy"},  # Mira Renda Variavel 95k
    {"handle": "Dicas_Financeiras_Poupanca", "tier": 3, "bias": "none", "area": "economy"},  # Dicas Financeiras PT 94k
    {"handle": "Inteligencia_Produtiva", "tier": 3, "bias": "none", "area": "society"},  # Inteligencia Produtiva 84k
    {"handle": "www11A_com", "tier": 3, "bias": "none", "area": "general"},  # 11A.com PT 67k
    {"handle": "Portalnoticiasceara", "tier": 3, "bias": "none", "area": "general"},  # Portal Noticias Ceara 62k
    {"handle": "Onishchenko001", "tier": 3, "bias": "none", "area": "general"},  # Onishchenko PT 58k
    {"handle": "sina", "tier": 3, "bias": "none", "area": "general"},  # Sina PT 150k
    {"handle": "tpbsn", "tier": 3, "bias": "none", "area": "general"},  # TPBSN PT 109k
    {"handle": "Teecop", "tier": 3, "bias": "none", "area": "general"},  # Teecop PT 92k
    {"handle": "joaodainfotips", "tier": 3, "bias": "none", "area": "general"},  # Joao Info Tips 53k
    {"handle": "profdanuzioneto", "tier": 3, "bias": "none", "area": "general"},  # Prof Danuzio OSINT 136k

    # ==============================================================
    #  ITALIAN-LANGUAGE
    # ==============================================================
    {"handle": "ultimora", "tier": 2, "bias": "none", "area": "general"},  # Ultimora IT 123k
    {"handle": "bintjbeilnews", "tier": 3, "bias": "none", "area": "general"},  # Bint Jbeil IT 271k
    {"handle": "notizieitaliane24", "tier": 3, "bias": "none", "area": "general"},  # Notizie Italiane 24 102k
    {"handle": "ByobluOfficial", "tier": 3, "bias": "none", "area": "general"},  # ByoBlu IT 88k
    {"handle": "lantidiplomatico", "tier": 3, "bias": "left-leaning", "area": "intl_politics"},  # L'AntiDiplomatico 90k
    {"handle": "giorgiobianchiphotojournalist", "tier": 3, "bias": "none", "area": "intl_politics"},  # Bianchi photojournalist 120k
    {"handle": "difendersiora", "tier": 3, "bias": "none", "area": "intl_politics"},  # Difendersi Ora 133k
    {"handle": "consenso_disinformato", "tier": 3, "bias": "none", "area": "intl_politics"},  # Consenso Disinformato 56k
    {"handle": "giorgiameloniufficiale", "tier": 1, "bias": "right-wing", "area": "intl_politics"},  # Meloni official 52k
    {"handle": "gianluigi_paragone", "tier": 1, "bias": "populist", "area": "intl_politics"},  # Paragone IT 51k
    {"handle": "rossobruni", "tier": 4, "bias": "left-leaning", "area": "defense"},  # Rossobruni defense 73k
    {"handle": "militaresemplice", "tier": 3, "bias": "none", "area": "defense"},  # Militare Semplice 34k
    {"handle": "ticonsiglio", "tier": 3, "bias": "none", "area": "business_innovation"},  # Ti Consiglio IT 102k

    # ==============================================================
    #  CHINESE-LANGUAGE
    # ==============================================================
    {"handle": "bx666", "tier": 3, "bias": "none", "area": "general"},  # CN news 506k
    {"handle": "Tsx99", "tier": 3, "bias": "none", "area": "general"},  # CN news 462k
    {"handle": "DNYxuanshang", "tier": 3, "bias": "none", "area": "general"},  # CN news 375k
    {"handle": "PP430", "tier": 3, "bias": "none", "area": "general"},  # CN news 345k
    {"handle": "xw1836", "tier": 3, "bias": "none", "area": "general"},  # CN news 326k
    {"handle": "dbg845", "tier": 3, "bias": "none", "area": "general"},  # CN news 301k
    {"handle": "DNYBG86", "tier": 3, "bias": "none", "area": "general"},  # CN news 301k
    {"handle": "jianpuzhai2222", "tier": 3, "bias": "none", "area": "general"},  # CN Cambodia news 276k
    {"handle": "dny9888", "tier": 3, "bias": "none", "area": "general"},  # CN news 271k
    {"handle": "malaixiya789", "tier": 3, "bias": "none", "area": "general"},  # CN Malaysia 254k
    {"handle": "baiyezhi8", "tier": 4, "bias": "none", "area": "defense"},  # CN military 490k
    {"handle": "GBTQCB", "tier": 4, "bias": "none", "area": "defense"},  # CN military 61k
    {"handle": "BanDaoNMYX", "tier": 4, "bias": "none", "area": "defense"},  # Peninsula CN 25k
    {"handle": "qwhrxsbgcg", "tier": 3, "bias": "none", "area": "intl_politics"},  # CN politics 302k
    {"handle": "dbxw1024", "tier": 3, "bias": "none", "area": "intl_politics"},  # CN politics 256k
    {"handle": "HLWNB", "tier": 3, "bias": "none", "area": "intl_politics"},  # CN politics 191k
    {"handle": "DNYTJL3", "tier": 3, "bias": "none", "area": "intl_politics"},  # CN politics 179k
    {"handle": "bbtswd", "tier": 3, "bias": "none", "area": "intl_politics"},  # CN politics 167k
    {"handle": "luoyeop", "tier": 3, "bias": "none", "area": "intl_politics"},  # CN politics 164k
    {"handle": "sjbaoguang_QM", "tier": 3, "bias": "none", "area": "intl_politics"},  # CN expose 150k
    {"handle": "v66666h", "tier": 3, "bias": "none", "area": "intl_politics"},  # CN politics 147k
    {"handle": "mianbeiriji888", "tier": 3, "bias": "none", "area": "intl_politics"},  # Myanmar CN 143k
    {"handle": "baoguang2022", "tier": 3, "bias": "none", "area": "intl_politics"},  # CN expose 141k
    {"handle": "zh_cnn9n9", "tier": 3, "bias": "none", "area": "culture"},  # CN culture 228k
    {"handle": "mondedufootball", "tier": 3, "bias": "none", "area": "sports"},  # CN football 102k

    # ==============================================================
    #  JAPANESE-LANGUAGE
    # ==============================================================
    {"handle": "aetherjapanresearch", "tier": 3, "bias": "none", "area": "education"},  # Japan Research KR 25k

    # ==============================================================
    #  KOREAN-LANGUAGE
    # ==============================================================
    {"handle": "HANAchina", "tier": 3, "bias": "none", "area": "economy"},  # Hana China KR 31k
    {"handle": "TechErrorArmy", "tier": 3, "bias": "none", "area": "tech"},  # Tech Error KR 89k
    {"handle": "blockmedia", "tier": 3, "bias": "none", "area": "tech"},  # Block Media KR 36k
    {"handle": "growthresearch", "tier": 3, "bias": "none", "area": "tech"},  # Growth Research KR 35k
    {"handle": "specialKR", "tier": 3, "bias": "none", "area": "general"},  # Special KR 58k
    {"handle": "telonews_kr", "tier": 3, "bias": "none", "area": "general"},  # Telo News KR 27k
    {"handle": "Yeouido_Lab", "tier": 3, "bias": "none", "area": "general"},  # Yeouido Lab KR 39k
    {"handle": "gaza_martyrs", "tier": 4, "bias": "pro-palestine", "area": "intl_politics"},  # Gaza Martyrs KR 32k
    {"handle": "Brain_And_Body_Research", "tier": 3, "bias": "none", "area": "education"},  # Brain Research KR 37k
    {"handle": "yubin_MPGA_science", "tier": 3, "bias": "none", "area": "education"},  # Science KR 32k

    # ==============================================================
    #  ENGLISH (new additions)
    # ==============================================================
    {"handle": "Tasnimnews", "tier": 2, "bias": "iran-state", "area": "general"},  # Tasnim News Agency IR 2.5M
    {"handle": "almayadeen", "tier": 2, "bias": "pro-hezbollah", "area": "general"},  # Al Mayadeen 504k
    {"handle": "lordxau", "tier": 4, "bias": "none", "area": "defense"},  # AR military 1.3M
    {"handle": "CLL7D", "tier": 4, "bias": "none", "area": "defense"},  # AR military analysis 337k
    {"handle": "nedalps", "tier": 4, "bias": "none", "area": "defense"},  # AR defense 208k
    {"handle": "aleamaliaat_aleaskaria", "tier": 4, "bias": "none", "area": "defense"},  # AR military ops 231k
    {"handle": "khabarehir", "tier": 3, "bias": "none", "area": "general"},  # AR news 1.5M
    {"handle": "pz_ft", "tier": 4, "bias": "none", "area": "general"},  # AR news 1.3M
    {"handle": "Sepblog", "tier": 4, "bias": "none", "area": "blog_analysis"},  # AR analysis blog 283k
    {"handle": "yurasumy", "tier": 3, "bias": "pro-russia", "area": "general"},  # Yura Sumy analysis 2.8M
    {"handle": "rusich_army", "tier": 5, "bias": "pro-russia", "area": "defense"},  # Rusich army 1.1M
    {"handle": "wargonzo", "tier": 3, "bias": "pro-russia", "area": "defense"},  # WarGonzo 781k
    {"handle": "voenacher", "tier": 3, "bias": "pro-russia", "area": "defense"},  # Voenache 678k
    {"handle": "bomber_fighter", "tier": 4, "bias": "pro-russia", "area": "defense"},  # Aviation military 527k
    {"handle": "warhistoryalconafter", "tier": 4, "bias": "none", "area": "defense"},  # War history 496k
    {"handle": "voenkorKotenok", "tier": 3, "bias": "pro-russia", "area": "defense"},  # War correspondent 325k
    {"handle": "yndx_market", "tier": 3, "bias": "none", "area": "business_innovation"},  # Yandex Market 1.1M
    {"handle": "Seda_Kasparova_news", "tier": 3, "bias": "pro-russia", "area": "society"},  # Social analysis 241k
    {"handle": "ScreenShotTrue", "tier": 4, "bias": "pro-russia", "area": "intl_politics"},  # Screenshot investigations 1.3M
    {"handle": "podoIsk_news", "tier": 3, "bias": "none", "area": "geopolitics"},  # RU geopolitics 147k
    {"handle": "technomotel", "tier": 3, "bias": "none", "area": "economy"},  # RU economy 1.6M
    {"handle": "marketbenefit", "tier": 3, "bias": "none", "area": "business_innovation"},  # RU market 943k
    {"handle": "TCH_channel", "tier": 2, "bias": "pro-ukraine", "area": "general"},  # TCH news 762k
    {"handle": "batalionmonako", "tier": 4, "bias": "pro-ukraine", "area": "general"},  # Monaco battalion 748k
    {"handle": "V_Zelenskiy_official", "tier": 1, "bias": "pro-ukraine", "area": "intl_politics"},  # Zelensky official 682k
    {"handle": "ab3army", "tier": 4, "bias": "pro-ukraine", "area": "defense"},  # 3rd Brigade 289k
    {"handle": "ukr_sof", "tier": 3, "bias": "pro-ukraine", "area": "defense"},  # UA Special Forces 144k
    {"handle": "AerisRimor", "tier": 3, "bias": "pro-ukraine", "area": "defense"},  # Air situation 132k
    {"handle": "cybersecurity_ua", "tier": 3, "bias": "none", "area": "tech"},  # UA cybersec 53k
    {"handle": "kiber_boroshno", "tier": 3, "bias": "pro-ukraine", "area": "tech"},  # Cyber flour OSINT 62k
    {"handle": "andronews_official", "tier": 3, "bias": "none", "area": "tech"},  # UA tech news 85k
    {"handle": "hotlinefinance", "tier": 3, "bias": "none", "area": "economy"},  # UA finance 86k
    {"handle": "palyanitsyanews", "tier": 3, "bias": "none", "area": "economy"},  # UA economy 73k
    {"handle": "tgp_news", "tier": 4, "bias": "none", "area": "blog_analysis"},  # UA analysis blog 52k
    {"handle": "upc_news", "tier": 3, "bias": "none", "area": "geopolitics"},  # UA geopolitics 23k
    {"handle": "Alertas24", "tier": 3, "bias": "none", "area": "general"},  # Alertas24 222k
    {"handle": "entre_guerras", "tier": 3, "bias": "none", "area": "intl_politics"},  # Between wars 137k
    {"handle": "Feilvbin1024", "tier": 3, "bias": "none", "area": "general"},  # JP Philippines news 241k
    {"handle": "QQDS999", "tier": 3, "bias": "none", "area": "general"},  # JP news 210k
    {"handle": "MWDXW00", "tier": 3, "bias": "none", "area": "general"},  # JP news 138k
    {"handle": "qqt13", "tier": 3, "bias": "none", "area": "intl_politics"},  # JP politics 201k
    {"handle": "zdny66", "tier": 3, "bias": "none", "area": "intl_politics"},  # JP politics 115k
    {"handle": "DG726", "tier": 3, "bias": "none", "area": "defense"},  # JP defense 106k
    {"handle": "zhonggong", "tier": 3, "bias": "none", "area": "intl_politics"},  # JP China analysis 25k
    {"handle": "FastStockNews", "tier": 3, "bias": "none", "area": "economy"},  # KR stock news 114k
    {"handle": "MarketPulseKR", "tier": 3, "bias": "none", "area": "economy"},  # KR market pulse 64k
    {"handle": "TrumpJr", "tier": 1, "bias": "us-right", "area": "intl_politics"},  # Trump Jr 409k
    {"handle": "OfficialRezaPahlavi", "tier": 3, "bias": "anti-regime-iran", "area": "intl_politics"},  # Reza Pahlavi 351k
    {"handle": "cendterra", "tier": 3, "bias": "none", "area": "intl_politics"},  # CendTerra 685k
    {"handle": "tikvahethiopia", "tier": 3, "bias": "none", "area": "intl_politics"},  # Ethiopia Hope 1.6M
    {"handle": "battlesjam", "tier": 4, "bias": "none", "area": "defense"},  # Battles Jam 457k
    {"handle": "Cyberbase_gr", "tier": 3, "bias": "none", "area": "defense"},  # Cyberbase GR 293k
    {"handle": "dedefense", "tier": 3, "bias": "none", "area": "defense"},  # DE Defense 261k
    {"handle": "TylerDurden_Army", "tier": 4, "bias": "contrarian", "area": "defense"},  # Tyler Durden Army 133k
    {"handle": "Slavyangrad", "tier": 3, "bias": "pro-russia", "area": "defense"},  # Slavyangrad 116k
    {"handle": "Naija_Sports", "tier": 3, "bias": "none", "area": "sports"},  # Nigeria Sports 1.2M
    {"handle": "Tech_News_433", "tier": 3, "bias": "none", "area": "society"},  # Tech News 78k
    {"handle": "WILD_EC0SYSTEM", "tier": 3, "bias": "none", "area": "intl_politics"},  # Wild Ecosystem 1.4M
    {"handle": "timelessai", "tier": 3, "bias": "none", "area": "intl_politics"},  # Timeless AI 1.2M
    {"handle": "sergeisergienkoen", "tier": 1, "bias": "mixed", "area": "blog_analysis"},
    {"handle": "ceosanya", "tier": 1, "bias": "mixed", "area": "blog_analysis"},
    {"handle": "dealdost", "tier": 1, "bias": "mixed", "area": "blog_analysis"},
    {"handle": "RANBIRROYOFFICE", "tier": 1, "bias": "mixed", "area": "blog_analysis"},
    {"handle": "Y_Nation", "tier": 1, "bias": "mixed", "area": "blog_analysis"},
    {"handle": "yonovip", "tier": 2, "bias": "govt", "area": "blog_analysis"},
    {"handle": "zh_cnzhcncc", "tier": 2, "bias": "mixed", "area": "blog_analysis"},
    {"handle": "www98Acom", "tier": 2, "bias": "mixed", "area": "blog_analysis"},
    {"handle": "lldalall", "tier": 3, "bias": "mixed", "area": "blog_analysis"},
    {"handle": "achileans", "tier": 3, "bias": "mixed", "area": "blog_analysis"},
    {"handle": "tucrespa09", "tier": 2, "bias": "mixed", "area": "blog_analysis"},
    {"handle": "buzzdatos", "tier": 2, "bias": "mixed", "area": "blog_analysis"},
    {"handle": "apkviajandoinfo", "tier": 2, "bias": "mixed", "area": "blog_analysis"},
    {"handle": "annarango0600", "tier": 2, "bias": "mixed", "area": "blog_analysis"},
    {"handle": "valecasta187", "tier": 3, "bias": "mixed", "area": "blog_analysis"},
    {"handle": "nafismalikova", "tier": 2, "bias": "mixed", "area": "blog_analysis"},
    {"handle": "Visionnairemagazine01", "tier": 2, "bias": "mixed", "area": "blog_analysis"},
    {"handle": "Quiz_onl", "tier": 3, "bias": "mixed", "area": "blog_analysis"},
    {"handle": "neodia", "tier": 3, "bias": "mixed", "area": "blog_analysis"},
    {"handle": "wendpouire_Bf", "tier": 3, "bias": "mixed", "area": "blog_analysis"},
    {"handle": "iraqed4", "tier": 1, "bias": "mixed", "area": "blog_analysis"},
    {"handle": "kafiha", "tier": 2, "bias": "mixed", "area": "blog_analysis"},
    {"handle": "linkduni", "tier": 2, "bias": "mixed", "area": "blog_analysis"},
    {"handle": "Nablusgheer", "tier": 2, "bias": "mixed", "area": "blog_analysis"},
    {"handle": "OX_5m", "tier": 2, "bias": "mixed", "area": "blog_analysis"},
    {"handle": "hayzonn", "tier": 1, "bias": "mixed", "area": "blog_analysis"},
    {"handle": "mash", "tier": 1, "bias": "mixed", "area": "blog_analysis"},
    {"handle": "mosguru", "tier": 1, "bias": "mixed", "area": "blog_analysis"},
    {"handle": "tonbase", "tier": 1, "bias": "mixed", "area": "blog_analysis"},
    {"handle": "maslennikovliga", "tier": 1, "bias": "mixed", "area": "blog_analysis"},
    {"handle": "byin_fun", "tier": 2, "bias": "mixed", "area": "blog_analysis"},
    {"handle": "resmisaha", "tier": 2, "bias": "mixed", "area": "blog_analysis"},
    {"handle": "SaidErcanResmi", "tier": 2, "bias": "mixed", "area": "blog_analysis"},
    {"handle": "liseliazginlar112", "tier": 3, "bias": "mixed", "area": "blog_analysis"},
    {"handle": "MeritQueenVIP", "tier": 3, "bias": "mixed", "area": "blog_analysis"},
    {"handle": "Timmkellner0ffiziel", "tier": 2, "bias": "mixed", "area": "blog_analysis"},
    {"handle": "iPopkarn_20", "tier": 3, "bias": "mixed", "area": "blog_analysis"},
    {"handle": "hkcm_Offiziell_1", "tier": 3, "bias": "mixed", "area": "blog_analysis"},
    {"handle": "M_Frohnmaier", "tier": 3, "bias": "mixed", "area": "blog_analysis"},
    {"handle": "OliRedet001", "tier": 3, "bias": "mixed", "area": "blog_analysis"},
    {"handle": "nonetutto", "tier": 2, "bias": "mixed", "area": "blog_analysis"},
    {"handle": "bernardomascellanis", "tier": 3, "bias": "mixed", "area": "blog_analysis"},
    {"handle": "PietroMichelangelis0", "tier": 3, "bias": "mixed", "area": "blog_analysis"},
    {"handle": "hoiwg", "tier": 3, "bias": "mixed", "area": "blog_analysis"},
    {"handle": "Aakash_Chopra_Akashvani", "tier": 3, "bias": "mixed", "area": "blog_analysis"},
    {"handle": "ZYFLS66", "tier": 2, "bias": "mixed", "area": "blog_analysis"},
    {"handle": "povv4", "tier": 2, "bias": "mixed", "area": "blog_analysis"},
    {"handle": "bbqyinliu888", "tier": 3, "bias": "mixed", "area": "blog_analysis"},
    {"handle": "aiyouxigongyifuzhu", "tier": 3, "bias": "mixed", "area": "blog_analysis"},
    {"handle": "HOPEVIPbypass", "tier": 3, "bias": "mixed", "area": "blog_analysis"},
    {"handle": "SmshThakre", "tier": 2, "bias": "mixed", "area": "blog_analysis"},
    {"handle": "QUIZZ_GALAXY", "tier": 2, "bias": "mixed", "area": "blog_analysis"},
    {"handle": "nirajbharwad", "tier": 2, "bias": "mixed", "area": "blog_analysis"},
    {"handle": "AlokRajRssb", "tier": 3, "bias": "mixed", "area": "blog_analysis"},
    {"handle": "salimmumbaism", "tier": 3, "bias": "mixed", "area": "blog_analysis"},
    {"handle": "magonia_b", "tier": 3, "bias": "mixed", "area": "blog_analysis"},
    {"handle": "linkdonii_shomaliiaaa", "tier": 3, "bias": "mixed", "area": "blog_analysis"},
    {"handle": "official_kr", "tier": 3, "bias": "govt", "area": "blog_analysis"},
    {"handle": "fre_sub_jav_indoY", "tier": 3, "bias": "mixed", "area": "blog_analysis"},
    {"handle": "eg_ai", "tier": 3, "bias": "mixed", "area": "blog_analysis"},
    {"handle": "xuanbu", "tier": 3, "bias": "mixed", "area": "blog_analysis"},
    {"handle": "lachentyt", "tier": 1, "bias": "mixed", "area": "blog_analysis"},
    {"handle": "OGoMono", "tier": 2, "bias": "mixed", "area": "blog_analysis"},
    {"handle": "lvivtp", "tier": 2, "bias": "mixed", "area": "blog_analysis"},
    {"handle": "dniproavariyka", "tier": 2, "bias": "mixed", "area": "blog_analysis"},
    {"handle": "kyiv_svitlo_ua", "tier": 2, "bias": "mixed", "area": "blog_analysis"},
    {"handle": "tech", "tier": 1, "bias": "mixed", "area": "business_innovation"},
    {"handle": "Magixdeals_Magix", "tier": 2, "bias": "mixed", "area": "business_innovation"},
    {"handle": "Khatri_Loots", "tier": 2, "bias": "mixed", "area": "business_innovation"},
    {"handle": "rapiddeals_unlimited", "tier": 2, "bias": "mixed", "area": "business_innovation"},
    {"handle": "Iranestekhdam_ir", "tier": 2, "bias": "mixed", "area": "business_innovation"},
    {"handle": "UploaderiAdvertising", "tier": 2, "bias": "mixed", "area": "business_innovation"},
    {"handle": "teniscertocupons", "tier": 2, "bias": "mixed", "area": "business_innovation"},
    {"handle": "baronepremios", "tier": 2, "bias": "mixed", "area": "business_innovation"},
    {"handle": "sneakersdomionlinks", "tier": 2, "bias": "mixed", "area": "business_innovation"},
    {"handle": "chollometro", "tier": 2, "bias": "mixed", "area": "business_innovation"},
    {"handle": "tuhogartextiles", "tier": 2, "bias": "mixed", "area": "business_innovation"},
    {"handle": "hacooesp", "tier": 2, "bias": "mixed", "area": "business_innovation"},
    {"handle": "importadoracrisma", "tier": 2, "bias": "mixed", "area": "business_innovation"},
    {"handle": "ZhuangMonar", "tier": 2, "bias": "mixed", "area": "business_innovation"},
    {"handle": "iammmchannel", "tier": 2, "bias": "mixed", "area": "business_innovation"},
    {"handle": "Kasperfxtrading", "tier": 2, "bias": "mixed", "area": "business_innovation"},
    {"handle": "catalystofficial", "tier": 3, "bias": "govt", "area": "business_innovation"},
    {"handle": "COACH_PRO1", "tier": 3, "bias": "mixed", "area": "business_innovation"},
    {"handle": "mittivoyuz1", "tier": 3, "bias": "mixed", "area": "business_innovation"},
    {"handle": "ewdifh", "tier": 1, "bias": "mixed", "area": "business_innovation"},
    {"handle": "ecoshariff", "tier": 1, "bias": "mixed", "area": "business_innovation"},
    {"handle": "cd4cd", "tier": 2, "bias": "mixed", "area": "business_innovation"},
    {"handle": "babakzanjanii1", "tier": 2, "bias": "mixed", "area": "business_innovation"},
    {"handle": "eestekhdam_com", "tier": 2, "bias": "mixed", "area": "business_innovation"},
    {"handle": "wewantyoutodothejob", "tier": 1, "bias": "mixed", "area": "business_innovation"},
    {"handle": "lenvies", "tier": 1, "bias": "mixed", "area": "business_innovation"},
    {"handle": "litvintm", "tier": 1, "bias": "mixed", "area": "business_innovation"},
    {"handle": "ozonru", "tier": 1, "bias": "mixed", "area": "business_innovation"},
    {"handle": "wbshop", "tier": 1, "bias": "mixed", "area": "business_innovation"},
    {"handle": "moshina_bozorim", "tier": 1, "bias": "mixed", "area": "business_innovation"},
    {"handle": "pandabuyfind", "tier": 2, "bias": "mixed", "area": "business_innovation"},
    {"handle": "OfficialBayspin", "tier": 2, "bias": "govt", "area": "business_innovation"},
    {"handle": "Fresherjobsadda", "tier": 2, "bias": "mixed", "area": "business_innovation"},
    {"handle": "linksfinds", "tier": 2, "bias": "mixed", "area": "business_innovation"},
    {"handle": "Flaviovonwitzleben_0", "tier": 3, "bias": "mixed", "area": "business_innovation"},
    {"handle": "silberjungethorstenschulte", "tier": 3, "bias": "mixed", "area": "business_innovation"},
    {"handle": "PhantomSchweiz", "tier": 3, "bias": "mixed", "area": "business_innovation"},
    {"handle": "iwga_marxamat_ishga_marhamat", "tier": 3, "bias": "mixed", "area": "business_innovation"},
    {"handle": "DrBerninger", "tier": 3, "bias": "mixed", "area": "business_innovation"},
    {"handle": "concorsipubblicin", "tier": 2, "bias": "mixed", "area": "business_innovation"},
    {"handle": "offertedale", "tier": 2, "bias": "mixed", "area": "business_innovation"},
    {"handle": "ERRORI_DI_PREZZO_SPAZIALI", "tier": 2, "bias": "mixed", "area": "business_innovation"},
    {"handle": "offertetoste", "tier": 2, "bias": "mixed", "area": "business_innovation"},
    {"handle": "Bazar_Moda_Tecnologia", "tier": 2, "bias": "mixed", "area": "business_innovation"},
    {"handle": "feixingzhe_qzzz", "tier": 2, "bias": "mixed", "area": "business_innovation"},
    {"handle": "DLBGB", "tier": 2, "bias": "mixed", "area": "business_innovation"},
    {"handle": "abskoop", "tier": 2, "bias": "mixed", "area": "business_innovation"},
    {"handle": "dbgxzy", "tier": 2, "bias": "mixed", "area": "business_innovation"},
    {"handle": "alljobsintelugu", "tier": 2, "bias": "mixed", "area": "business_innovation"},
    {"handle": "club_digrajsinghrajput", "tier": 2, "bias": "mixed", "area": "business_innovation"},
    {"handle": "officialsubhashcharan", "tier": 2, "bias": "govt", "area": "business_innovation"},
    {"handle": "JobsTargetM", "tier": 2, "bias": "mixed", "area": "business_innovation"},
    {"handle": "Aapni_Padhai", "tier": 2, "bias": "mixed", "area": "business_innovation"},
    {"handle": "marketyatraoriginal", "tier": 2, "bias": "govt", "area": "business_innovation"},
    {"handle": "dd_nnc", "tier": 2, "bias": "mixed", "area": "business_innovation"},
    {"handle": "ConsensusValueCreation1", "tier": 3, "bias": "mixed", "area": "business_innovation"},
    {"handle": "SNTG_2026", "tier": 3, "bias": "mixed", "area": "business_innovation"},
    {"handle": "ArisuIDO_Korea", "tier": 3, "bias": "mixed", "area": "business_innovation"},
    {"handle": "BerrystoreNotice", "tier": 3, "bias": "mixed", "area": "business_innovation"},
    {"handle": "zii33", "tier": 2, "bias": "mixed", "area": "business_innovation"},
    {"handle": "WHWHWHWH3", "tier": 3, "bias": "mixed", "area": "business_innovation"},
    {"handle": "applpk8", "tier": 3, "bias": "mixed", "area": "business_innovation"},
    {"handle": "pingtai08", "tier": 3, "bias": "mixed", "area": "business_innovation"},
    {"handle": "duteba", "tier": 3, "bias": "mixed", "area": "business_innovation"},
    {"handle": "rrozetka", "tier": 2, "bias": "mixed", "area": "business_innovation"},
    {"handle": "mega_tekhnika", "tier": 2, "bias": "mixed", "area": "business_innovation"},
    {"handle": "vacansi_msk", "tier": 2, "bias": "mixed", "area": "business_innovation"},
    {"handle": "kievy_rabota", "tier": 2, "bias": "mixed", "area": "business_innovation"},
    {"handle": "rabota_kievy", "tier": 2, "bias": "mixed", "area": "business_innovation"},
    {"handle": "durov", "tier": 1, "bias": "mixed", "area": "tech"},
    {"handle": "ForUAI_channel", "tier": 1, "bias": "mixed", "area": "tech"},
    {"handle": "brainedge_ai", "tier": 1, "bias": "mixed", "area": "tech"},
    {"handle": "Hoosha_ai", "tier": 2, "bias": "mixed", "area": "tech"},
    {"handle": "TonDreamerEng", "tier": 2, "bias": "mixed", "area": "tech"},
    {"handle": "zh_cny", "tier": 2, "bias": "mixed", "area": "tech"},
    {"handle": "tecnoarthardware", "tier": 2, "bias": "mixed", "area": "tech"},
    {"handle": "ProxyMTProting", "tier": 2, "bias": "mixed", "area": "tech"},
    {"handle": "zhcncc_ch_zn_zh_zn", "tier": 2, "bias": "mixed", "area": "tech"},
    {"handle": "schematicslaptop", "tier": 2, "bias": "mixed", "area": "tech"},
    {"handle": "ferchtechmsu", "tier": 3, "bias": "mixed", "area": "tech"},
    {"handle": "CatalinaCastro1", "tier": 3, "bias": "mixed", "area": "tech"},
    {"handle": "neterplay", "tier": 3, "bias": "mixed", "area": "tech"},
    {"handle": "MarkCastilloDeveloper", "tier": 3, "bias": "mixed", "area": "tech"},
    {"handle": "TokinPrivacy", "tier": 3, "bias": "mixed", "area": "tech"},
    {"handle": "cgplugin", "tier": 2, "bias": "mixed", "area": "tech"},
    {"handle": "webdev_trainings", "tier": 2, "bias": "mixed", "area": "tech"},
    {"handle": "edit_matin01", "tier": 2, "bias": "mixed", "area": "tech"},
    {"handle": "Microsoft_Office_Download", "tier": 3, "bias": "mixed", "area": "tech"},
    {"handle": "nedaaiofficial", "tier": 3, "bias": "govt", "area": "tech"},
    {"handle": "newsbin", "tier": 1, "bias": "mixed", "area": "tech"},
    {"handle": "R7com", "tier": 1, "bias": "mixed", "area": "tech"},
    {"handle": "FreakConfig", "tier": 1, "bias": "mixed", "area": "tech"},
    {"handle": "hoosha_hamkari", "tier": 1, "bias": "mixed", "area": "tech"},
    {"handle": "Proxy_Khor", "tier": 1, "bias": "mixed", "area": "tech"},
    {"handle": "hitvpn_news", "tier": 1, "bias": "mixed", "area": "tech"},
    {"handle": "whackdoor", "tier": 1, "bias": "mixed", "area": "tech"},
    {"handle": "chatgptv", "tier": 1, "bias": "mixed", "area": "tech"},
    {"handle": "icebergcis", "tier": 1, "bias": "mixed", "area": "tech"},
    {"handle": "bugfeature", "tier": 2, "bias": "mixed", "area": "tech"},
    {"handle": "GPT360_Announcement", "tier": 2, "bias": "mixed", "area": "tech"},
    {"handle": "apklite_me", "tier": 3, "bias": "mixed", "area": "tech"},
    {"handle": "ashishtech10", "tier": 3, "bias": "mixed", "area": "tech"},
    {"handle": "lkhofach200", "tier": 3, "bias": "mixed", "area": "tech"},
    {"handle": "nuancesprog", "tier": 3, "bias": "mixed", "area": "tech"},
    {"handle": "se8888888888", "tier": 2, "bias": "mixed", "area": "tech"},
    {"handle": "apolut", "tier": 3, "bias": "mixed", "area": "tech"},
    {"handle": "BFE_Energiekultur", "tier": 3, "bias": "mixed", "area": "tech"},
    {"handle": "FreieEnergieDeutschland", "tier": 3, "bias": "mixed", "area": "tech"},
    {"handle": "achatgpt", "tier": 3, "bias": "mixed", "area": "tech"},
    {"handle": "ethio_telecom", "tier": 2, "bias": "mixed", "area": "tech"},
    {"handle": "offertepuntotech", "tier": 2, "bias": "mixed", "area": "tech"},
    {"handle": "Porteqal3", "tier": 2, "bias": "mixed", "area": "tech"},
    {"handle": "zh_cn_ch_zn_zhongwenhanhua", "tier": 2, "bias": "mixed", "area": "tech"},
    {"handle": "Offerte_Tech_IPhone_Pc_Cellulari", "tier": 3, "bias": "mixed", "area": "tech"},
    {"handle": "zh_cnw8a", "tier": 2, "bias": "mixed", "area": "tech"},
    {"handle": "zh_cnbaj", "tier": 2, "bias": "mixed", "area": "tech"},
    {"handle": "SpaceSGKRG", "tier": 2, "bias": "mixed", "area": "tech"},
    {"handle": "ddddffxxr", "tier": 2, "bias": "mixed", "area": "tech"},
    {"handle": "ymccc", "tier": 2, "bias": "mixed", "area": "tech"},
    {"handle": "amzaingtechtube", "tier": 2, "bias": "mixed", "area": "tech"},
    {"handle": "techinsiderashish1", "tier": 2, "bias": "mixed", "area": "tech"},
    {"handle": "officialuploadfiles", "tier": 2, "bias": "govt", "area": "tech"},
    {"handle": "OfficialTechnoCraze", "tier": 3, "bias": "govt", "area": "tech"},
    {"handle": "technicaljs", "tier": 3, "bias": "mixed", "area": "tech"},
    {"handle": "emperorcoin", "tier": 3, "bias": "mixed", "area": "tech"},
    {"handle": "vsvs1119", "tier": 3, "bias": "mixed", "area": "tech"},
    {"handle": "bio_shinhan", "tier": 3, "bias": "mixed", "area": "tech"},
    {"handle": "TERBOxr", "tier": 3, "bias": "mixed", "area": "tech"},
    {"handle": "justicekingsman", "tier": 3, "bias": "mixed", "area": "tech"},
    {"handle": "zh_cngtz", "tier": 2, "bias": "mixed", "area": "tech"},
    {"handle": "svipp3", "tier": 2, "bias": "mixed", "area": "tech"},
    {"handle": "TC6266", "tier": 2, "bias": "mixed", "area": "tech"},
    {"handle": "cgpg666", "tier": 3, "bias": "mixed", "area": "tech"},
    {"handle": "DYKS06", "tier": 3, "bias": "mixed", "area": "tech"},
    {"handle": "databord", "tier": 3, "bias": "mixed", "area": "tech"},
    {"handle": "isAuto99", "tier": 3, "bias": "mixed", "area": "tech"},
    {"handle": "funpapers_news", "tier": 3, "bias": "mixed", "area": "tech"},
    {"handle": "hackyourmom", "tier": 3, "bias": "mixed", "area": "tech"},
    {"handle": "chatgptua", "tier": 3, "bias": "mixed", "area": "tech"},
    {"handle": "CEXIO_Announcements", "tier": 1, "bias": "govt", "area": "economy"},
    {"handle": "buzz", "tier": 1, "bias": "mixed", "area": "economy"},
    {"handle": "venture", "tier": 1, "bias": "mixed", "area": "economy"},
    {"handle": "Holdcoin_Channel", "tier": 1, "bias": "mixed", "area": "economy"},
    {"handle": "AsikaLive", "tier": 1, "bias": "mixed", "area": "economy"},
    {"handle": "tradepn", "tier": 2, "bias": "mixed", "area": "economy"},
    {"handle": "omilionario5", "tier": 2, "bias": "mixed", "area": "economy"},
    {"handle": "brunoaguiarinvestimentosvip", "tier": 2, "bias": "mixed", "area": "economy"},
    {"handle": "iuriindica", "tier": 2, "bias": "mixed", "area": "economy"},
    {"handle": "canalmundobet", "tier": 3, "bias": "mixed", "area": "economy"},
    {"handle": "tradeando_oficial", "tier": 2, "bias": "mixed", "area": "economy"},
    {"handle": "EnriqueMoris_canal", "tier": 2, "bias": "mixed", "area": "economy"},
    {"handle": "EmpresaElectricaDeLaHabana", "tier": 2, "bias": "mixed", "area": "economy"},
    {"handle": "Libre_Indicadores", "tier": 2, "bias": "mixed", "area": "economy"},
    {"handle": "newmanperez", "tier": 2, "bias": "mixed", "area": "economy"},
    {"handle": "prosnosticcccc", "tier": 2, "bias": "mixed", "area": "economy"},
    {"handle": "jsjsjsnnsbv", "tier": 2, "bias": "mixed", "area": "economy"},
    {"handle": "bmfpapy", "tier": 2, "bias": "mixed", "area": "economy"},
    {"handle": "kasper_tradingg1", "tier": 2, "bias": "mixed", "area": "economy"},
    {"handle": "perlocash10", "tier": 2, "bias": "mixed", "area": "economy"},
    {"handle": "Tofan_Trade", "tier": 1, "bias": "mixed", "area": "economy"},
    {"handle": "Aqay_Tahlilgar", "tier": 1, "bias": "mixed", "area": "economy"},
    {"handle": "tignal", "tier": 1, "bias": "mixed", "area": "economy"},
    {"handle": "trrade", "tier": 1, "bias": "mixed", "area": "economy"},
    {"handle": "hipoilt", "tier": 1, "bias": "mixed", "area": "economy"},
    {"handle": "DeCenter", "tier": 1, "bias": "mixed", "area": "economy"},
    {"handle": "investkingyru", "tier": 1, "bias": "mixed", "area": "economy"},
    {"handle": "eduardinvest", "tier": 1, "bias": "mixed", "area": "economy"},
    {"handle": "LabsVC", "tier": 1, "bias": "mixed", "area": "economy"},
    {"handle": "milliardom", "tier": 1, "bias": "mixed", "area": "economy"},
    {"handle": "nifty_banknifty_trading_intraday", "tier": 2, "bias": "mixed", "area": "economy"},
    {"handle": "halka_arzn", "tier": 2, "bias": "mixed", "area": "economy"},
    {"handle": "halka_arz1", "tier": 2, "bias": "mixed", "area": "economy"},
    {"handle": "lemoncash_community", "tier": 2, "bias": "mixed", "area": "economy"},
    {"handle": "indrummycom", "tier": 2, "bias": "mixed", "area": "economy"},
    {"handle": "marcfriedrich0ffiziell", "tier": 2, "bias": "mixed", "area": "economy"},
    {"handle": "markus_kralII", "tier": 2, "bias": "mixed", "area": "economy"},
    {"handle": "WolffErnsts_offiziells", "tier": 2, "bias": "mixed", "area": "economy"},
    {"handle": "PhilipHopff", "tier": 2, "bias": "mixed", "area": "economy"},
    {"handle": "MarcFriedrich0ffizielle", "tier": 2, "bias": "mixed", "area": "economy"},
    {"handle": "scontierrati", "tier": 2, "bias": "mixed", "area": "economy"},
    {"handle": "AndrewcgaCGA", "tier": 2, "bias": "mixed", "area": "economy"},
    {"handle": "Alex_goldtraderr", "tier": 3, "bias": "mixed", "area": "economy"},
    {"handle": "lasourcex2026", "tier": 3, "bias": "mixed", "area": "economy"},
    {"handle": "banconoteuw", "tier": 3, "bias": "mixed", "area": "economy"},
    {"handle": "pron", "tier": 2, "bias": "mixed", "area": "economy"},
    {"handle": "zhgx0", "tier": 2, "bias": "mixed", "area": "economy"},
    {"handle": "ddgx18", "tier": 2, "bias": "mixed", "area": "economy"},
    {"handle": "dashubi", "tier": 2, "bias": "mixed", "area": "economy"},
    {"handle": "appletzpd", "tier": 2, "bias": "mixed", "area": "economy"},
    {"handle": "gouravgyandhara", "tier": 2, "bias": "mixed", "area": "economy"},
    {"handle": "GHANSHYAMTECH", "tier": 2, "bias": "mixed", "area": "economy"},
    {"handle": "JalwawithSahil", "tier": 2, "bias": "mixed", "area": "economy"},
    {"handle": "targetwithankit_TWA", "tier": 2, "bias": "mixed", "area": "economy"},
    {"handle": "Stock_Gainers_official9", "tier": 2, "bias": "govt", "area": "economy"},
    {"handle": "BithumbExchangeData", "tier": 3, "bias": "mixed", "area": "economy"},
    {"handle": "corevalue", "tier": 3, "bias": "mixed", "area": "economy"},
    {"handle": "darthacking", "tier": 3, "bias": "mixed", "area": "economy"},
    {"handle": "insidertracking", "tier": 3, "bias": "mixed", "area": "economy"},
    {"handle": "kwusa", "tier": 3, "bias": "mixed", "area": "economy"},
    {"handle": "caipiaoppp", "tier": 2, "bias": "mixed", "area": "economy"},
    {"handle": "jpzqz88", "tier": 2, "bias": "mixed", "area": "economy"},
    {"handle": "BBK800", "tier": 2, "bias": "mixed", "area": "economy"},
    {"handle": "yh77qian", "tier": 3, "bias": "mixed", "area": "economy"},
    {"handle": "heiusdt6699", "tier": 3, "bias": "mixed", "area": "economy"},
    {"handle": "genius_space", "tier": 2, "bias": "mixed", "area": "economy"},
    {"handle": "lawyerwrites", "tier": 2, "bias": "mixed", "area": "economy"},
    {"handle": "absolutionlab", "tier": 2, "bias": "mixed", "area": "economy"},
    {"handle": "beejob1_ua", "tier": 3, "bias": "mixed", "area": "economy"},
    {"handle": "pro_podatky_fop", "tier": 3, "bias": "mixed", "area": "economy"},
    {"handle": "learn2earnings", "tier": 1, "bias": "mixed", "area": "education"},
    {"handle": "MnemonicsAnn", "tier": 1, "bias": "mixed", "area": "education"},
    {"handle": "frensAI", "tier": 1, "bias": "mixed", "area": "education"},
    {"handle": "CareerwillApp", "tier": 2, "bias": "mixed", "area": "education"},
    {"handle": "Biblioteca_Gratis", "tier": 2, "bias": "mixed", "area": "education"},
    {"handle": "Extreme_CursosGratis", "tier": 2, "bias": "mixed", "area": "education"},
    {"handle": "parsa_farahani00", "tier": 2, "bias": "mixed", "area": "education"},
    {"handle": "film_neptune", "tier": 3, "bias": "mixed", "area": "education"},
    {"handle": "sanidadgob", "tier": 2, "bias": "mixed", "area": "education"},
    {"handle": "neonclasses", "tier": 2, "bias": "mixed", "area": "education"},
    {"handle": "guiasgratis", "tier": 2, "bias": "mixed", "area": "education"},
    {"handle": "celesteperez15", "tier": 2, "bias": "mixed", "area": "education"},
    {"handle": "jozve_iq", "tier": 2, "bias": "mixed", "area": "education"},
    {"handle": "lesformations", "tier": 3, "bias": "mixed", "area": "education"},
    {"handle": "sergent484diallo", "tier": 3, "bias": "mixed", "area": "education"},
    {"handle": "livresdoc", "tier": 3, "bias": "mixed", "area": "education"},
    {"handle": "iraqedu", "tier": 1, "bias": "mixed", "area": "education"},
    {"handle": "iraqed8", "tier": 1, "bias": "mixed", "area": "education"},
    {"handle": "sandali_shahidbehshti", "tier": 1, "bias": "mixed", "area": "education"},
    {"handle": "mlazemna", "tier": 1, "bias": "mixed", "area": "education"},
    {"handle": "simplecdz", "tier": 1, "bias": "mixed", "area": "education"},
    {"handle": "matematik_andrei_channel", "tier": 1, "bias": "mixed", "area": "education"},
    {"handle": "geovaxue", "tier": 2, "bias": "mixed", "area": "education"},
    {"handle": "test_dot", "tier": 2, "bias": "mixed", "area": "education"},
    {"handle": "eduuz_DTMuzb_abituriyent_oliygoh", "tier": 2, "bias": "mixed", "area": "education"},
    {"handle": "Lucent_Science_History_Polity_Gk", "tier": 2, "bias": "mixed", "area": "education"},
    {"handle": "Romanekitap", "tier": 2, "bias": "mixed", "area": "education"},
    {"handle": "yks_pdfg", "tier": 2, "bias": "mixed", "area": "education"},
    {"handle": "Angizeh_konkore", "tier": 2, "bias": "mixed", "area": "education"},
    {"handle": "soale_vip", "tier": 3, "bias": "mixed", "area": "education"},
    {"handle": "Echte_Geschichte", "tier": 3, "bias": "mixed", "area": "education"},
    {"handle": "drspitzbart", "tier": 3, "bias": "mixed", "area": "education"},
    {"handle": "gkbypardeepsirofficial", "tier": 2, "bias": "govt", "area": "education"},
    {"handle": "uzedu", "tier": 3, "bias": "mixed", "area": "education"},
    {"handle": "lefotodelpassato", "tier": 3, "bias": "mixed", "area": "education"},
    {"handle": "BasicIELTSListening", "tier": 3, "bias": "mixed", "area": "education"},
    {"handle": "gokaidanbao", "tier": 2, "bias": "mixed", "area": "education"},
    {"handle": "lhzpd", "tier": 2, "bias": "mixed", "area": "education"},
    {"handle": "gebaopiCloud", "tier": 3, "bias": "mixed", "area": "education"},
    {"handle": "huashu3", "tier": 3, "bias": "mixed", "area": "education"},
    {"handle": "mathsbygaganpratap", "tier": 1, "bias": "mixed", "area": "education"},
    {"handle": "utkarshclasses", "tier": 1, "bias": "mixed", "area": "education"},
    {"handle": "WinnersInstituteIndoreAdityaSir", "tier": 2, "bias": "govt", "area": "education"},
    {"handle": "khanglobalstudies", "tier": 2, "bias": "mixed", "area": "education"},
    {"handle": "SamaptiMamZoology6", "tier": 2, "bias": "mixed", "area": "education"},
    {"handle": "Mpefkk", "tier": 2, "bias": "mixed", "area": "education"},
    {"handle": "Manish_Raj_Physics_Wallah_sir_MR", "tier": 3, "bias": "mixed", "area": "education"},
    {"handle": "Biologybyvipinsir8", "tier": 3, "bias": "mixed", "area": "education"},
    {"handle": "sefrehty", "tier": 3, "bias": "mixed", "area": "education"},
    {"handle": "tjxshszk", "tier": 3, "bias": "mixed", "area": "education"},
    {"handle": "rajasthan_gk_study_quizz", "tier": 3, "bias": "mixed", "area": "education"},
    {"handle": "learning_japanese_with_sayuri00", "tier": 3, "bias": "mixed", "area": "education"},
    {"handle": "truexakropivnicky", "tier": 2, "bias": "mixed", "area": "education"},
    {"handle": "green_way_com_ua", "tier": 2, "bias": "mixed", "area": "education"},
    {"handle": "vstuposvita", "tier": 2, "bias": "mixed", "area": "education"},
    {"handle": "kyivkk", "tier": 3, "bias": "mixed", "area": "education"},
    {"handle": "calmme_ai", "tier": 2, "bias": "mixed", "area": "society"},
    {"handle": "thewayofsolution", "tier": 2, "bias": "mixed", "area": "society"},
    {"handle": "slava_balaban_369", "tier": 2, "bias": "mixed", "area": "society"},
    {"handle": "Mensa2", "tier": 3, "bias": "mixed", "area": "society"},
    {"handle": "nofaprebirth", "tier": 3, "bias": "mixed", "area": "society"},
    {"handle": "CriAtivar", "tier": 3, "bias": "mixed", "area": "society"},
    {"handle": "PSICOLOGIALIBROSTEST", "tier": 3, "bias": "mixed", "area": "society"},
    {"handle": "TheFourWindsEspanol", "tier": 3, "bias": "mixed", "area": "society"},
    {"handle": "antiestrescat1", "tier": 3, "bias": "mixed", "area": "society"},
    {"handle": "livrosdapsicologia", "tier": 3, "bias": "mixed", "area": "society"},
    {"handle": "heartbeat_love_status", "tier": 3, "bias": "mixed", "area": "society"},
    {"handle": "Penseeintelligente", "tier": 3, "bias": "mixed", "area": "society"},
    {"handle": "PVTNFS", "tier": 2, "bias": "mixed", "area": "society"},
    {"handle": "taIabati", "tier": 2, "bias": "mixed", "area": "society"},
    {"handle": "psychology_F", "tier": 2, "bias": "mixed", "area": "society"},
    {"handle": "doctor_zubareva", "tier": 2, "bias": "mixed", "area": "society"},
    {"handle": "neuraldvig", "tier": 2, "bias": "mixed", "area": "society"},
    {"handle": "sexology_vasilenko", "tier": 2, "bias": "mixed", "area": "society"},
    {"handle": "doctor_sadovskaya", "tier": 2, "bias": "mixed", "area": "society"},
    {"handle": "psixolog_testi", "tier": 3, "bias": "mixed", "area": "society"},
    {"handle": "kerosine2020", "tier": 3, "bias": "mixed", "area": "society"},
    {"handle": "soeren_schumann", "tier": 3, "bias": "mixed", "area": "society"},
    {"handle": "dralinalessenich", "tier": 3, "bias": "mixed", "area": "society"},
    {"handle": "SeelenLeuchtturm", "tier": 3, "bias": "mixed", "area": "society"},
    {"handle": "sitorabonuabdurahmanova", "tier": 3, "bias": "mixed", "area": "society"},
    {"handle": "sapiens3", "tier": 3, "bias": "mixed", "area": "society"},
    {"handle": "MedicinaEmozionale", "tier": 3, "bias": "mixed", "area": "society"},
    {"handle": "ASMRLNGC", "tier": 2, "bias": "mixed", "area": "society"},
    {"handle": "u7095", "tier": 3, "bias": "mixed", "area": "society"},
    {"handle": "asmrxiaoai", "tier": 3, "bias": "mixed", "area": "society"},
    {"handle": "Hindi_Quotes_Motivational_Videos", "tier": 2, "bias": "mixed", "area": "society"},
    {"handle": "Hindi_Pshycology_Fact", "tier": 2, "bias": "mixed", "area": "society"},
    {"handle": "positive_vibes07", "tier": 2, "bias": "mixed", "area": "society"},
    {"handle": "Aadatien_life_Quotes_Status", "tier": 3, "bias": "mixed", "area": "society"},
    {"handle": "pomnyun", "tier": 3, "bias": "mixed", "area": "society"},
    {"handle": "Thoughts_BFox", "tier": 3, "bias": "mixed", "area": "society"},
    {"handle": "jiepnga", "tier": 3, "bias": "mixed", "area": "society"},
    {"handle": "tryvoga_chomu", "tier": 2, "bias": "mixed", "area": "society"},
    {"handle": "kholodenko", "tier": 3, "bias": "mixed", "area": "society"},
    {"handle": "taktychna_rukavuchkaa", "tier": 3, "bias": "mixed", "area": "society"},
    {"handle": "notime_app", "tier": 2, "bias": "mixed", "area": "tech"},
    {"handle": "drip_tools", "tier": 2, "bias": "mixed", "area": "tech"},
    {"handle": "tricks_excel", "tier": 3, "bias": "mixed", "area": "tech"},
    {"handle": "project_board", "tier": 2, "bias": "mixed", "area": "tech"},
    {"handle": "join_events", "tier": 3, "bias": "mixed", "area": "tech"},
    {"handle": "Feriobehi", "tier": 3, "bias": "mixed", "area": "tech"},
    {"handle": "sscaleton", "tier": 2, "bias": "mixed", "area": "tech"},
    {"handle": "Master_of_Habits", "tier": 2, "bias": "mixed", "area": "tech"},
    {"handle": "na_udalenke4", "tier": 3, "bias": "mixed", "area": "tech"},
    {"handle": "Lifehacks_tipps", "tier": 3, "bias": "mixed", "area": "tech"},
    {"handle": "excel_analyst", "tier": 3, "bias": "mixed", "area": "tech"},
    {"handle": "ibnkhvb", "tier": 3, "bias": "mixed", "area": "tech"},
    {"handle": "edgebyte", "tier": 3, "bias": "mixed", "area": "tech"},
    {"handle": "mentor365", "tier": 3, "bias": "mixed", "area": "tech"},
    {"handle": "TimeFarmChannel", "tier": 1, "bias": "mixed", "area": "general"},
    {"handle": "just", "tier": 1, "bias": "mixed", "area": "general"},
    {"handle": "popcorn_today", "tier": 1, "bias": "mixed", "area": "general"},
    {"handle": "navoiyda_bugun", "tier": 2, "bias": "mixed", "area": "general"},
    {"handle": "cineregard", "tier": 2, "bias": "mixed", "area": "general"},
    {"handle": "VeriteDiffusee", "tier": 3, "bias": "mixed", "area": "general"},
    {"handle": "pas2faiblez", "tier": 3, "bias": "mixed", "area": "general"},
    {"handle": "AnonymeCitoyen", "tier": 3, "bias": "mixed", "area": "general"},
    {"handle": "moscowach", "tier": 1, "bias": "mixed", "area": "general"},
    {"handle": "moscowmap", "tier": 1, "bias": "mixed", "area": "general"},
    {"handle": "moscow", "tier": 1, "bias": "mixed", "area": "general"},
    {"handle": "criptooner", "tier": 2, "bias": "mixed", "area": "general"},
    {"handle": "halka_arz88", "tier": 2, "bias": "mixed", "area": "general"},
    {"handle": "lpr1_Crimea_Alarm", "tier": 2, "bias": "mixed", "area": "general"},
    {"handle": "LuxuryWorldNews", "tier": 2, "bias": "mixed", "area": "general"},
    {"handle": "timmkellner", "tier": 2, "bias": "mixed", "area": "general"},
    {"handle": "kenjebsen", "tier": 2, "bias": "mixed", "area": "general"},
    {"handle": "concorsandotelegram", "tier": 2, "bias": "mixed", "area": "general"},
    {"handle": "AldoQefaliaUfficiaIe", "tier": 3, "bias": "mixed", "area": "general"},
    {"handle": "centogiornidaleoni", "tier": 3, "bias": "mixed", "area": "general"},
    {"handle": "svip250", "tier": 2, "bias": "mixed", "area": "general"},
    {"handle": "VIPDnyang8", "tier": 2, "bias": "mixed", "area": "general"},
    {"handle": "Upsc_Prelims_Current_Affairs_PDF", "tier": 2, "bias": "mixed", "area": "general"},
    {"handle": "inbcnewshindi", "tier": 2, "bias": "mixed", "area": "general"},
    {"handle": "DrAbhishekVerma_News", "tier": 2, "bias": "mixed", "area": "general"},
    {"handle": "duckmyduck_official_kr", "tier": 3, "bias": "govt", "area": "general"},
    {"handle": "noticeEvol", "tier": 3, "bias": "mixed", "area": "general"},
    {"handle": "Telearchivech", "tier": 3, "bias": "mixed", "area": "general"},
    {"handle": "dny31i", "tier": 2, "bias": "mixed", "area": "general"},
    {"handle": "dnydsjjjjjjjjj", "tier": 2, "bias": "mixed", "area": "general"},
    {"handle": "bg887", "tier": 2, "bias": "mixed", "area": "general"},
    {"handle": "alarmua", "tier": 2, "bias": "mixed", "area": "general"},
    {"handle": "dnipro_alerts", "tier": 2, "bias": "mixed", "area": "general"},
    {"handle": "DeepStateUA", "tier": 2, "bias": "mixed", "area": "general"},
    {"handle": "Major_Foundation", "tier": 1, "bias": "mixed", "area": "intl_politics"},
    {"handle": "the_vertus", "tier": 1, "bias": "mixed", "area": "intl_politics"},
    {"handle": "theFreeDogs_ANN", "tier": 1, "bias": "mixed", "area": "intl_politics"},
    {"handle": "Alaa2v", "tier": 3, "bias": "mixed", "area": "intl_politics"},
    {"handle": "MarcalPorSp28", "tier": 3, "bias": "mixed", "area": "intl_politics"},
    {"handle": "depeduardobolsonaro", "tier": 3, "bias": "mixed", "area": "intl_politics"},
    {"handle": "intervencionpolicia", "tier": 2, "bias": "mixed", "area": "intl_politics"},
    {"handle": "Vpoutine", "tier": 3, "bias": "mixed", "area": "intl_politics"},
    {"handle": "Salim_Laibi_LLP", "tier": 3, "bias": "mixed", "area": "intl_politics"},
    {"handle": "alexandrahenrioncaude", "tier": 3, "bias": "mixed", "area": "intl_politics"},
    {"handle": "v999v", "tier": 1, "bias": "mixed", "area": "intl_politics"},
    {"handle": "MercifulHeartsOfficial", "tier": 2, "bias": "govt", "area": "intl_politics"},
    {"handle": "hamza20300", "tier": 2, "bias": "mixed", "area": "intl_politics"},
    {"handle": "adelimkhanov_95", "tier": 1, "bias": "mixed", "area": "intl_politics"},
    {"handle": "PEMERSATUBANGSA_INDO_Z", "tier": 3, "bias": "mixed", "area": "intl_politics"},
    {"handle": "ifsaqknal", "tier": 3, "bias": "mixed", "area": "intl_politics"},
    {"handle": "joqargikenes", "tier": 3, "bias": "mixed", "area": "intl_politics"},
    {"handle": "Dr_markuskralI", "tier": 2, "bias": "mixed", "area": "intl_politics"},
    {"handle": "markuskrall_abb", "tier": 2, "bias": "mixed", "area": "intl_politics"},
    {"handle": "freiesachsen", "tier": 2, "bias": "mixed", "area": "intl_politics"},
    {"handle": "ugofuoco", "tier": 3, "bias": "mixed", "area": "intl_politics"},
    {"handle": "guerrieriperlaliberta", "tier": 3, "bias": "mixed", "area": "intl_politics"},
    {"handle": "donbassitalia", "tier": 3, "bias": "mixed", "area": "intl_politics"},
    {"handle": "YuvaUpnishadFoundation", "tier": 2, "bias": "mixed", "area": "intl_politics"},
    {"handle": "Pardafash_Fraud_Expose", "tier": 2, "bias": "mixed", "area": "intl_politics"},
    {"handle": "MaharashtraPoliceBharati", "tier": 2, "bias": "govt", "area": "intl_politics"},
    {"handle": "aiphotolab_bot", "tier": 3, "bias": "mixed", "area": "intl_politics"},
    {"handle": "waitstudy", "tier": 3, "bias": "mixed", "area": "intl_politics"},
    {"handle": "zerozg1", "tier": 3, "bias": "mixed", "area": "intl_politics"},
    {"handle": "vipbg888", "tier": 2, "bias": "mixed", "area": "intl_politics"},
    {"handle": "pianzi1", "tier": 3, "bias": "mixed", "area": "intl_politics"},
    {"handle": "KarsynTT", "tier": 3, "bias": "mixed", "area": "intl_politics"},
    {"handle": "robert_magyar", "tier": 2, "bias": "state", "area": "intl_politics"},
    {"handle": "hyevuy_dnepr", "tier": 2, "bias": "mixed", "area": "intl_politics"},
    {"handle": "raketa_trevoga", "tier": 2, "bias": "mixed", "area": "intl_politics"},
    {"handle": "PentagonGamesOfficial", "tier": 2, "bias": "govt", "area": "defense"},
    {"handle": "BIHAR_DAROGA_SI_BSSC_GK_GS_AEDO", "tier": 2, "bias": "mixed", "area": "defense"},
    {"handle": "plus777com", "tier": 2, "bias": "govt", "area": "defense"},
    {"handle": "intervencionespoliciales105", "tier": 3, "bias": "mixed", "area": "defense"},
    {"handle": "enguerrados", "tier": 3, "bias": "mixed", "area": "defense"},
    {"handle": "IntervencionPolicialOficial", "tier": 3, "bias": "mixed", "area": "defense"},
    {"handle": "alvine_pronos_blacknutlovers", "tier": 3, "bias": "mixed", "area": "defense"},
    {"handle": "keddy_foot", "tier": 3, "bias": "mixed", "area": "defense"},
    {"handle": "redstarfc", "tier": 2, "bias": "mixed", "area": "defense"},
    {"handle": "WarArchive_ua", "tier": 3, "bias": "mixed", "area": "defense"},
    {"handle": "Defencewallahcds", "tier": 3, "bias": "mixed", "area": "defense"},
    {"handle": "Soldaten_und_Reservisten", "tier": 3, "bias": "mixed", "area": "defense"},
    {"handle": "rustag1913GS", "tier": 3, "bias": "mixed", "area": "defense"},
    {"handle": "infodefITALY", "tier": 3, "bias": "mixed", "area": "defense"},
    {"handle": "infodifesa", "tier": 3, "bias": "mixed", "area": "defense"},
    {"handle": "GBTBGBD", "tier": 3, "bias": "mixed", "area": "defense"},
    {"handle": "qgxianrzb", "tier": 3, "bias": "mixed", "area": "defense"},
    {"handle": "JSXW8", "tier": 3, "bias": "mixed", "area": "defense"},
    {"handle": "Armydost", "tier": 3, "bias": "mixed", "area": "defense"},
    {"handle": "ONLY_KHAKI_VARDI", "tier": 3, "bias": "mixed", "area": "defense"},
    {"handle": "Mission_Gujarat_Police_Exam", "tier": 3, "bias": "mixed", "area": "defense"},
    {"handle": "HI_GS", "tier": 3, "bias": "mixed", "area": "defense"},
    {"handle": "TsubasarivalsAnnounce", "tier": 1, "bias": "mixed", "area": "sports"},
    {"handle": "PUBG_MOBILE_AKKAUNT_UC", "tier": 2, "bias": "mixed", "area": "sports"},
    {"handle": "tap_sport_official", "tier": 2, "bias": "state", "area": "sports"},
    {"handle": "apostasepalpites", "tier": 2, "bias": "mixed", "area": "sports"},
    {"handle": "Javierhalamadridd", "tier": 2, "bias": "mixed", "area": "sports"},
    {"handle": "tenislinks", "tier": 2, "bias": "mixed", "area": "sports"},
    {"handle": "Tipsanalistas", "tier": 2, "bias": "mixed", "area": "sports"},
    {"handle": "barcelona", "tier": 2, "bias": "mixed", "area": "sports"},
    {"handle": "ateneavivefit", "tier": 2, "bias": "mixed", "area": "sports"},
    {"handle": "lucastyltyoficial", "tier": 2, "bias": "mixed", "area": "sports"},
    {"handle": "infosport181", "tier": 2, "bias": "mixed", "area": "sports"},
    {"handle": "Canal_foot", "tier": 2, "bias": "mixed", "area": "sports"},
    {"handle": "es_qb", "tier": 1, "bias": "mixed", "area": "sports"},
    {"handle": "RegaPlus", "tier": 1, "bias": "mixed", "area": "sports"},
    {"handle": "arskh967001101", "tier": 2, "bias": "mixed", "area": "sports"},
    {"handle": "moscowtinderr", "tier": 2, "bias": "mixed", "area": "sports"},
    {"handle": "GOAL24Main", "tier": 2, "bias": "mixed", "area": "sports"},
    {"handle": "newcsgo", "tier": 2, "bias": "mixed", "area": "sports"},
    {"handle": "ZORTV_FUDBOL_SPORT", "tier": 2, "bias": "mixed", "area": "sports"},
    {"handle": "rudra_cricket_analyst", "tier": 2, "bias": "mixed", "area": "sports"},
    {"handle": "futbol_arenasi", "tier": 2, "bias": "mixed", "area": "sports"},
    {"handle": "fixsports", "tier": 3, "bias": "mixed", "area": "sports"},
    {"handle": "chelsverhampton", "tier": 3, "bias": "mixed", "area": "sports"},
    {"handle": "cricket11newsjoin", "tier": 3, "bias": "mixed", "area": "sports"},
    {"handle": "LexoCalcio", "tier": 2, "bias": "mixed", "area": "sports"},
    {"handle": "tebal_tennisi", "tier": 3, "bias": "mixed", "area": "sports"},
    {"handle": "MichelleAnelaofficial", "tier": 3, "bias": "govt", "area": "sports"},
    {"handle": "imim68", "tier": 2, "bias": "mixed", "area": "sports"},
    {"handle": "SAMRAT100K", "tier": 3, "bias": "mixed", "area": "sports"},
    {"handle": "Masterblaster017", "tier": 3, "bias": "mixed", "area": "sports"},
    {"handle": "AnuragxCricket", "tier": 1, "bias": "mixed", "area": "sports"},
    {"handle": "Baazigar_Cricket_Fixer_Chnl", "tier": 2, "bias": "mixed", "area": "sports"},
    {"handle": "AakashChopraOfficial", "tier": 2, "bias": "govt", "area": "sports"},
    {"handle": "PremierLeaguefra", "tier": 3, "bias": "mixed", "area": "sports"},
    {"handle": "gyungphj", "tier": 3, "bias": "mixed", "area": "sports"},
    {"handle": "duanzib", "tier": 2, "bias": "mixed", "area": "sports"},
    {"handle": "dny8579", "tier": 3, "bias": "mixed", "area": "sports"},
    {"handle": "qtty168", "tier": 3, "bias": "mixed", "area": "sports"},
    {"handle": "h_kiev", "tier": 2, "bias": "mixed", "area": "sports"},
    {"handle": "hk_kamenskoe1", "tier": 3, "bias": "mixed", "area": "sports"},
    {"handle": "MaksPodzigun", "tier": 3, "bias": "mixed", "area": "sports"},
    {"handle": "lastmintdotfun", "tier": 2, "bias": "mixed", "area": "business_innovation"},
    {"handle": "GrowDealzLootOffers", "tier": 2, "bias": "mixed", "area": "business_innovation"},
    {"handle": "Shopping_Offers_Online_Tricks", "tier": 2, "bias": "mixed", "area": "business_innovation"},
    {"handle": "LaPromotion", "tier": 2, "bias": "mixed", "area": "business_innovation"},
    {"handle": "xetdaspromocoes", "tier": 2, "bias": "mixed", "area": "business_innovation"},
    {"handle": "promocaozinha", "tier": 2, "bias": "mixed", "area": "business_innovation"},
    {"handle": "gabygardezexcluisive", "tier": 2, "bias": "mixed", "area": "business_innovation"},
    {"handle": "ofertastuberviejuner", "tier": 3, "bias": "mixed", "area": "business_innovation"},
    {"handle": "cajitatech", "tier": 3, "bias": "mixed", "area": "business_innovation"},
    {"handle": "FXRevolutionFR", "tier": 3, "bias": "mixed", "area": "business_innovation"},
    {"handle": "lionelpcscanale", "tier": 3, "bias": "mixed", "area": "business_innovation"},
    {"handle": "Mundopromosapp", "tier": 3, "bias": "mixed", "area": "business_innovation"},
    {"handle": "kekoDev", "tier": 2, "bias": "mixed", "area": "business_innovation"},
    {"handle": "linkdoni_brand", "tier": 2, "bias": "mixed", "area": "business_innovation"},
    {"handle": "TrendZ8", "tier": 2, "bias": "mixed", "area": "business_innovation"},
    {"handle": "notypicmarketing", "tier": 2, "bias": "mixed", "area": "business_innovation"},
    {"handle": "markettwits", "tier": 2, "bias": "mixed", "area": "business_innovation"},
    {"handle": "sosamuzik300", "tier": 2, "bias": "mixed", "area": "business_innovation"},
    {"handle": "oygx", "tier": 2, "bias": "mixed", "area": "business_innovation"},
    {"handle": "S8LUCKY", "tier": 2, "bias": "mixed", "area": "business_innovation"},
    {"handle": "smm_panelf", "tier": 3, "bias": "mixed", "area": "business_innovation"},
    {"handle": "app22", "tier": 2, "bias": "mixed", "area": "business_innovation"},
    {"handle": "scontialimentari", "tier": 3, "bias": "mixed", "area": "business_innovation"},
    {"handle": "tricksbystg", "tier": 3, "bias": "mixed", "area": "business_innovation"},
    {"handle": "ultimaofferta", "tier": 2, "bias": "mixed", "area": "business_innovation"},
    {"handle": "lapaginadegliscontiDEALS", "tier": 2, "bias": "mixed", "area": "business_innovation"},
    {"handle": "codici_sconto_sconti", "tier": 2, "bias": "mixed", "area": "business_innovation"},
    {"handle": "Lvsvip", "tier": 2, "bias": "mixed", "area": "business_innovation"},
    {"handle": "jujingonline", "tier": 2, "bias": "mixed", "area": "business_innovation"},
    {"handle": "WAN8013", "tier": 2, "bias": "mixed", "area": "business_innovation"},
    {"handle": "sreditingzoneoffical", "tier": 2, "bias": "mixed", "area": "business_innovation"},
    {"handle": "officialGCKD", "tier": 3, "bias": "govt", "area": "business_innovation"},
    {"handle": "youtag_tools", "tier": 3, "bias": "mixed", "area": "business_innovation"},
    {"handle": "yzsqqq", "tier": 3, "bias": "mixed", "area": "business_innovation"},
    {"handle": "lzxiuc", "tier": 3, "bias": "mixed", "area": "business_innovation"},
    {"handle": "yunfen", "tier": 3, "bias": "mixed", "area": "business_innovation"},
    {"handle": "marketing_ukr", "tier": 2, "bias": "mixed", "area": "business_innovation"},
    {"handle": "lowcostua", "tier": 3, "bias": "mixed", "area": "business_innovation"},
    {"handle": "Kukurudza_blog", "tier": 3, "bias": "mixed", "area": "business_innovation"},
    {"handle": "hrumfam", "tier": 1, "bias": "mixed", "area": "health"},
    {"handle": "chillguy_xmas", "tier": 2, "bias": "mixed", "area": "health"},
    {"handle": "num1_ch", "tier": 2, "bias": "mixed", "area": "health"},
    {"handle": "drenanbotelho_evento", "tier": 2, "bias": "mixed", "area": "health"},
    {"handle": "babypromokids", "tier": 2, "bias": "mixed", "area": "health"},
    {"handle": "wendellcarvalho", "tier": 3, "bias": "mixed", "area": "health"},
    {"handle": "edixsucesosexplicitos", "tier": 2, "bias": "mixed", "area": "health"},
    {"handle": "Cardenas_xx", "tier": 2, "bias": "mixed", "area": "health"},
    {"handle": "MydoctorA96", "tier": 2, "bias": "mixed", "area": "health"},
    {"handle": "Paroles_Sages", "tier": 2, "bias": "mixed", "area": "health"},
    {"handle": "LionelPcs110", "tier": 2, "bias": "mixed", "area": "health"},
    {"handle": "saladenicoise", "tier": 2, "bias": "mixed", "area": "health"},
    {"handle": "EN_QE", "tier": 2, "bias": "mixed", "area": "health"},
    {"handle": "N4_V2", "tier": 2, "bias": "mixed", "area": "health"},
    {"handle": "STORYAT_11", "tier": 2, "bias": "mixed", "area": "health"},
    {"handle": "pekagame", "tier": 1, "bias": "mixed", "area": "health"},
    {"handle": "Kulinariya_retsept", "tier": 1, "bias": "mixed", "area": "health"},
    {"handle": "edisonfamilia", "tier": 2, "bias": "mixed", "area": "health"},
    {"handle": "dilya_asliddinovna_dietolog", "tier": 1, "bias": "mixed", "area": "health"},
    {"handle": "ide_food", "tier": 2, "bias": "mixed", "area": "health"},
    {"handle": "kokyawhsu1", "tier": 2, "bias": "mixed", "area": "health"},
    {"handle": "HolistischeGesundheitHeilung", "tier": 2, "bias": "mixed", "area": "health"},
    {"handle": "Lilou_Luv", "tier": 3, "bias": "mixed", "area": "health"},
    {"handle": "maeklegutelaune", "tier": 3, "bias": "mixed", "area": "health"},
    {"handle": "ambracalippotourr", "tier": 2, "bias": "mixed", "area": "health"},
    {"handle": "Michellecomiiii", "tier": 3, "bias": "mixed", "area": "health"},
    {"handle": "drbarbarabalanzoni", "tier": 3, "bias": "mixed", "area": "health"},
    {"handle": "fancha103", "tier": 2, "bias": "mixed", "area": "health"},
    {"handle": "baiheqin1", "tier": 2, "bias": "mixed", "area": "health"},
    {"handle": "hhhhwwwyyttaauu", "tier": 2, "bias": "mixed", "area": "health"},
    {"handle": "harsh_bhagat_zero_to_hero_call", "tier": 2, "bias": "mixed", "area": "health"},
    {"handle": "Ganpatsinghraj89", "tier": 2, "bias": "mixed", "area": "health"},
    {"handle": "Success_Motivational_hindi_Video", "tier": 2, "bias": "mixed", "area": "health"},
    {"handle": "bdhdjdjdjdhdu", "tier": 3, "bias": "mixed", "area": "health"},
    {"handle": "Stethoscope_yakeen_OMSirPW", "tier": 3, "bias": "mixed", "area": "health"},
    {"handle": "minchoisfuture", "tier": 3, "bias": "mixed", "area": "health"},
    {"handle": "sucai_taotu_zuantu_huashuu", "tier": 2, "bias": "mixed", "area": "health"},
    {"handle": "flbtx", "tier": 3, "bias": "mixed", "area": "health"},
    {"handle": "TG_DJ999", "tier": 3, "bias": "mixed", "area": "health"},
    {"handle": "leradanya_lifeee", "tier": 2, "bias": "mixed", "area": "health"},
    {"handle": "smachno2021", "tier": 2, "bias": "mixed", "area": "health"},
    {"handle": "recepti", "tier": 2, "bias": "mixed", "area": "health"},
    {"handle": "majors", "tier": 1, "bias": "mixed", "area": "community"},
    {"handle": "dogs", "tier": 1, "bias": "mixed", "area": "community"},
    {"handle": "ProducoesIndependentesAsia", "tier": 2, "bias": "mixed", "area": "community"},
    {"handle": "fernandacastro22", "tier": 2, "bias": "mixed", "area": "community"},
    {"handle": "Alviseperez", "tier": 2, "bias": "mixed", "area": "community"},
    {"handle": "abriloficial1", "tier": 2, "bias": "mixed", "area": "community"},
    {"handle": "srsss6", "tier": 2, "bias": "mixed", "area": "community"},
    {"handle": "wf_po", "tier": 2, "bias": "mixed", "area": "community"},
    {"handle": "fasngon", "tier": 1, "bias": "mixed", "area": "community"},
    {"handle": "dosti", "tier": 1, "bias": "mixed", "area": "community"},
    {"handle": "MDaudov_95", "tier": 1, "bias": "mixed", "area": "community"},
    {"handle": "RoolzRussia", "tier": 1, "bias": "mixed", "area": "community"},
    {"handle": "marmok_yt", "tier": 2, "bias": "mixed", "area": "community"},
    {"handle": "ifsa_turk41", "tier": 2, "bias": "mixed", "area": "community"},
    {"handle": "drmarkuskrall_abc", "tier": 2, "bias": "mixed", "area": "community"},
    {"handle": "DoQusThreads", "tier": 2, "bias": "mixed", "area": "community"},
    {"handle": "colorwizclub2", "tier": 2, "bias": "mixed", "area": "community"},
    {"handle": "Streaming_community_sito", "tier": 2, "bias": "mixed", "area": "community"},
    {"handle": "zh_cn86r", "tier": 2, "bias": "mixed", "area": "community"},
    {"handle": "zh_cnsfu", "tier": 2, "bias": "mixed", "area": "community"},
    {"handle": "ramchoudharysocial", "tier": 2, "bias": "mixed", "area": "community"},
    {"handle": "SomeshThakreTg", "tier": 2, "bias": "mixed", "area": "community"},
    {"handle": "yubin_MPGA", "tier": 2, "bias": "mixed", "area": "community"},
    {"handle": "rabota_ish_samarkand", "tier": 3, "bias": "mixed", "area": "community"},
    {"handle": "dldb00", "tier": 2, "bias": "mixed", "area": "community"},
    {"handle": "changshaws", "tier": 2, "bias": "mixed", "area": "community"},
    {"handle": "roblru", "tier": 1, "bias": "mixed", "area": "community"},
    {"handle": "kiev_levyy_bereg", "tier": 2, "bias": "mixed", "area": "community"},
    {"handle": "NimishaMam", "tier": 2, "bias": "mixed", "area": "culture"},
    {"handle": "Bolly_films_music_Songs_indian", "tier": 2, "bias": "mixed", "area": "culture"},
    {"handle": "NOSSABIBLIOTECABR5", "tier": 2, "bias": "mixed", "area": "culture"},
    {"handle": "Brasil_Livros_Canal", "tier": 2, "bias": "mixed", "area": "culture"},
    {"handle": "kndita777", "tier": 2, "bias": "mixed", "area": "culture"},
    {"handle": "librosgratisinfo", "tier": 2, "bias": "mixed", "area": "culture"},
    {"handle": "soutidastan", "tier": 3, "bias": "mixed", "area": "culture"},
    {"handle": "livresetformations", "tier": 3, "bias": "mixed", "area": "culture"},
    {"handle": "PPPJP", "tier": 1, "bias": "mixed", "area": "culture"},
    {"handle": "YYYYD", "tier": 1, "bias": "mixed", "area": "culture"},
    {"handle": "temki_zvezdys", "tier": 1, "bias": "mixed", "area": "culture"},
    {"handle": "rhymestg", "tier": 1, "bias": "mixed", "area": "culture"},
    {"handle": "prooxy2026", "tier": 2, "bias": "mixed", "area": "culture"},
    {"handle": "Un_30", "tier": 2, "bias": "mixed", "area": "culture"},
    {"handle": "deutsch8", "tier": 2, "bias": "mixed", "area": "culture"},
    {"handle": "DE_lehrbucher", "tier": 3, "bias": "mixed", "area": "culture"},
    {"handle": "zh_cn_chinese_zwbao", "tier": 2, "bias": "mixed", "area": "culture"},
    {"handle": "libri_pdf_gratis", "tier": 3, "bias": "mixed", "area": "culture"},
    {"handle": "zh_cnd6d", "tier": 2, "bias": "mixed", "area": "culture"},
    {"handle": "zh_cngjg", "tier": 2, "bias": "mixed", "area": "culture"},
    {"handle": "sampurna_hindi_vyakaran", "tier": 2, "bias": "mixed", "area": "culture"},
    {"handle": "Learni_Spoken_English_Vocabulary", "tier": 2, "bias": "mixed", "area": "culture"},
    {"handle": "shayari_Quote_status_video", "tier": 3, "bias": "mixed", "area": "culture"},
    {"handle": "Gyan_Wale_Words_status", "tier": 3, "bias": "mixed", "area": "culture"},
    {"handle": "ja_JP8", "tier": 2, "bias": "mixed", "area": "culture"},
    {"handle": "sucai7", "tier": 3, "bias": "mixed", "area": "culture"},
    {"handle": "Poliglotych_English", "tier": 3, "bias": "mixed", "area": "culture"},
    {"handle": "audiobookksua", "tier": 3, "bias": "mixed", "area": "culture"},
    {"handle": "hdhdhshs7372", "tier": 2, "bias": "mixed", "area": "geopolitics"},
    {"handle": "originalmahadevid", "tier": 2, "bias": "mixed", "area": "geopolitics"},
    {"handle": "vu_64", "tier": 2, "bias": "mixed", "area": "geopolitics"},
    {"handle": "Salihaliraqi", "tier": 2, "bias": "mixed", "area": "geopolitics"},
    {"handle": "comusav", "tier": 3, "bias": "mixed", "area": "geopolitics"},
    {"handle": "gccinfo", "tier": 3, "bias": "mixed", "area": "geopolitics"},
    {"handle": "aqedamenhag", "tier": 3, "bias": "mixed", "area": "geopolitics"},
    {"handle": "Sadegh_Alhosseini", "tier": 3, "bias": "mixed", "area": "geopolitics"},
    {"handle": "Mozkhrfats", "tier": 1, "bias": "mixed", "area": "geopolitics"},
    {"handle": "Almustashaar", "tier": 2, "bias": "mixed", "area": "geopolitics"},
    {"handle": "etoznakmag", "tier": 2, "bias": "mixed", "area": "geopolitics"},
    {"handle": "sheyhtamir1974", "tier": 2, "bias": "mixed", "area": "geopolitics"},
    {"handle": "islammemisaltinTR", "tier": 2, "bias": "mixed", "area": "geopolitics"},
    {"handle": "Nomoz_Vaqtlarim", "tier": 2, "bias": "mixed", "area": "geopolitics"},
    {"handle": "silkeschaefer", "tier": 2, "bias": "mixed", "area": "geopolitics"},
    {"handle": "WolfDieterStorI", "tier": 2, "bias": "mixed", "area": "geopolitics"},
    {"handle": "MinisteroSalute", "tier": 2, "bias": "mixed", "area": "geopolitics"},
    {"handle": "LaVeritaCiRendeLiberiAdvanced", "tier": 3, "bias": "mixed", "area": "geopolitics"},
    {"handle": "Hanumanji_Status_Whatsapp_videos", "tier": 3, "bias": "mixed", "area": "geopolitics"},
    {"handle": "XKNBS7", "tier": 3, "bias": "mixed", "area": "geopolitics"},
    {"handle": "mahadev_status_hd_full_screen", "tier": 3, "bias": "mixed", "area": "geopolitics"},
    {"handle": "Geeta_Gyan", "tier": 3, "bias": "mixed", "area": "geopolitics"},
    {"handle": "Bhagwat_geeta_status_video", "tier": 3, "bias": "mixed", "area": "geopolitics"},
    {"handle": "Suprabhat_Sandesh_morning", "tier": 3, "bias": "mixed", "area": "geopolitics"},
    {"handle": "Tamil_Kadavul_Murugar", "tier": 3, "bias": "mixed", "area": "geopolitics"},
    {"handle": "Radha_krishna_best_status_Hd", "tier": 3, "bias": "mixed", "area": "geopolitics"},
    {"handle": "astroobere", "tier": 2, "bias": "mixed", "area": "geopolitics"},
    {"handle": "resurgammmm", "tier": 3, "bias": "mixed", "area": "geopolitics"},
    {"handle": "amazingworldtravel", "tier": 1, "bias": "mixed", "area": "culture"},
    {"handle": "EraOfExplorers", "tier": 2, "bias": "mixed", "area": "culture"},
    {"handle": "garimposdodepinho", "tier": 3, "bias": "mixed", "area": "culture"},
    {"handle": "melhoresdestinos", "tier": 3, "bias": "mixed", "area": "culture"},
    {"handle": "holidayguruES", "tier": 3, "bias": "mixed", "area": "culture"},
    {"handle": "walkcityapp", "tier": 3, "bias": "mixed", "area": "culture"},
    {"handle": "laviedetom", "tier": 3, "bias": "mixed", "area": "culture"},
    {"handle": "triptour_uz", "tier": 3, "bias": "mixed", "area": "culture"},
    {"handle": "BNA_travel", "tier": 2, "bias": "mixed", "area": "culture"},
    {"handle": "immigration20iranians", "tier": 2, "bias": "mixed", "area": "culture"},
    {"handle": "mskint", "tier": 1, "bias": "mixed", "area": "culture"},
    {"handle": "tutu_travel", "tier": 2, "bias": "mixed", "area": "culture"},
    {"handle": "antalya_hakkinda", "tier": 2, "bias": "mixed", "area": "culture"},
    {"handle": "bellagioanalysis", "tier": 3, "bias": "mixed", "area": "culture"},
    {"handle": "WetteradlerKanal", "tier": 2, "bias": "mixed", "area": "culture"},
    {"handle": "StefanOutdoor_Chiemgau", "tier": 3, "bias": "mixed", "area": "culture"},
    {"handle": "ShmekyLifes1", "tier": 3, "bias": "mixed", "area": "culture"},
    {"handle": "poracciinviaggio", "tier": 3, "bias": "mixed", "area": "culture"},
    {"handle": "cadb", "tier": 2, "bias": "mixed", "area": "culture"},
    {"handle": "whrjx", "tier": 2, "bias": "mixed", "area": "culture"},
    {"handle": "daraintravels", "tier": 3, "bias": "mixed", "area": "culture"},
    {"handle": "DG8093", "tier": 2, "bias": "mixed", "area": "culture"},
    {"handle": "USCA0", "tier": 3, "bias": "mixed", "area": "culture"},
    {"handle": "Lv1256", "tier": 2, "bias": "mixed", "area": "culture"},
    {"handle": "tripmydream", "tier": 2, "bias": "mixed", "area": "culture"},
    {"handle": "SimonsCatNews", "tier": 1, "bias": "mixed", "area": "environment"},
    {"handle": "bull_bear1", "tier": 2, "bias": "mixed", "area": "environment"},
    {"handle": "CoOow", "tier": 3, "bias": "mixed", "area": "environment"},
    {"handle": "foresthome", "tier": 3, "bias": "mixed", "area": "environment"},
    {"handle": "ReinoAnimalX", "tier": 2, "bias": "mixed", "area": "environment"},
    {"handle": "animalessalvajes", "tier": 3, "bias": "mixed", "area": "environment"},
    {"handle": "x_ixxk", "tier": 3, "bias": "mixed", "area": "environment"},
    {"handle": "naturelimage", "tier": 3, "bias": "mixed", "area": "environment"},
    {"handle": "golbapet", "tier": 2, "bias": "mixed", "area": "environment"},
    {"handle": "iraqed36", "tier": 2, "bias": "mixed", "area": "environment"},
    {"handle": "picardia_ecosystem", "tier": 2, "bias": "mixed", "area": "environment"},
    {"handle": "koshkii_kotiki", "tier": 2, "bias": "mixed", "area": "environment"},
    {"handle": "uzbek_cats", "tier": 3, "bias": "mixed", "area": "environment"},
    {"handle": "tayezhniy", "tier": 3, "bias": "mixed", "area": "environment"},
    {"handle": "kraeuterkeller", "tier": 3, "bias": "mixed", "area": "environment"},
    {"handle": "Gartentipps_DE", "tier": 3, "bias": "mixed", "area": "environment"},
    {"handle": "RisparmioAnimali", "tier": 3, "bias": "mixed", "area": "environment"},
    {"handle": "nanyang5588", "tier": 3, "bias": "mixed", "area": "environment"},
    {"handle": "wuhhhy2", "tier": 3, "bias": "mixed", "area": "environment"},
    {"handle": "JOKES_ADDA_OFFICIEL", "tier": 3, "bias": "mixed", "area": "environment"},
    {"handle": "zoologybysujeettripathi", "tier": 3, "bias": "mixed", "area": "environment"},
    {"handle": "sililanka44", "tier": 3, "bias": "mixed", "area": "environment"},
    {"handle": "chigualf", "tier": 3, "bias": "mixed", "area": "environment"},
    {"handle": "fishingflagman", "tier": 3, "bias": "mixed", "area": "environment"},
    {"handle": "magyarbirds414", "tier": 3, "bias": "mixed", "area": "environment"},
    {"handle": "BarbieMZP", "tier": 3, "bias": "mixed", "area": "tech"},
    {"handle": "english58000", "tier": 3, "bias": "mixed", "area": "tech"},
    {"handle": "driveprime7", "tier": 2, "bias": "mixed", "area": "tech"},
    {"handle": "pichauofertas", "tier": 2, "bias": "mixed", "area": "tech"},
    {"handle": "canal4x4tro", "tier": 2, "bias": "mixed", "area": "tech"},
    {"handle": "jymcar", "tier": 3, "bias": "mixed", "area": "tech"},
    {"handle": "AutomotiveSTL", "tier": 3, "bias": "mixed", "area": "tech"},
    {"handle": "aligeramy11", "tier": 3, "bias": "mixed", "area": "tech"},
    {"handle": "akhbar_khudro", "tier": 2, "bias": "mixed", "area": "tech"},
    {"handle": "KHODRO_AKHBAR", "tier": 2, "bias": "mixed", "area": "tech"},
    {"handle": "tachki", "tier": 1, "bias": "mixed", "area": "tech"},
    {"handle": "auto_manya", "tier": 1, "bias": "mixed", "area": "tech"},
    {"handle": "LiderAvtoUz", "tier": 2, "bias": "mixed", "area": "tech"},
    {"handle": "inamarka_mashinalar", "tier": 2, "bias": "mixed", "area": "tech"},
    {"handle": "chainesenew", "tier": 3, "bias": "mixed", "area": "tech"},
    {"handle": "SegnalazioniStradali_Ticino", "tier": 3, "bias": "mixed", "area": "tech"},
    {"handle": "autocilentodlg", "tier": 3, "bias": "mixed", "area": "tech"},
    {"handle": "clgbjww", "tier": 2, "bias": "mixed", "area": "tech"},
    {"handle": "xjszww", "tier": 2, "bias": "mixed", "area": "tech"},
    {"handle": "shaoyang9999", "tier": 3, "bias": "mixed", "area": "tech"},
    {"handle": "whly5_jmd", "tier": 3, "bias": "mixed", "area": "tech"},
    {"handle": "UkrzalInfo", "tier": 2, "bias": "mixed", "area": "tech"},
    {"handle": "kievavto2", "tier": 3, "bias": "mixed", "area": "tech"},
    {"handle": "princess_19990", "tier": 2, "bias": "mixed", "area": "culture"},
    {"handle": "i4_3Q", "tier": 2, "bias": "mixed", "area": "culture"},
    {"handle": "teslond1", "tier": 2, "bias": "mixed", "area": "culture"},
    {"handle": "lensvibe1", "tier": 3, "bias": "mixed", "area": "culture"},
    {"handle": "MangasManhwasYAOI", "tier": 2, "bias": "mixed", "area": "culture"},
    {"handle": "Dramas_0009", "tier": 3, "bias": "mixed", "area": "culture"},
    {"handle": "Graphics_designerr", "tier": 3, "bias": "mixed", "area": "culture"},
    {"handle": "alahinpalomino_1", "tier": 3, "bias": "mixed", "area": "culture"},
    {"handle": "nKnnn", "tier": 1, "bias": "mixed", "area": "culture"},
    {"handle": "kwvsxa", "tier": 2, "bias": "mixed", "area": "culture"},
    {"handle": "leoday", "tier": 1, "bias": "mixed", "area": "culture"},
    {"handle": "architecton_tech", "tier": 1, "bias": "mixed", "area": "culture"},
    {"handle": "mnpzlt1", "tier": 2, "bias": "mixed", "area": "culture"},
    {"handle": "Pixel_3D_STL", "tier": 3, "bias": "mixed", "area": "culture"},
    {"handle": "anatomie_offiziell", "tier": 3, "bias": "mixed", "area": "culture"},
    {"handle": "model3d_free", "tier": 3, "bias": "mixed", "area": "culture"},
    {"handle": "lapaginadegliscontiMODA", "tier": 3, "bias": "mixed", "area": "culture"},
    {"handle": "privateart", "tier": 3, "bias": "mixed", "area": "culture"},
    {"handle": "PicACG", "tier": 2, "bias": "mixed", "area": "culture"},
    {"handle": "taotu_huashu_sucaii", "tier": 2, "bias": "mixed", "area": "culture"},
    {"handle": "Alfaghi_studio", "tier": 3, "bias": "mixed", "area": "culture"},
    {"handle": "pdf_studio", "tier": 3, "bias": "mixed", "area": "culture"},
    {"handle": "amiraeldahab2024", "tier": 3, "bias": "mixed", "area": "culture"},
    {"handle": "piyav89", "tier": 3, "bias": "mixed", "area": "culture"},
    {"handle": "yZDlh9", "tier": 3, "bias": "mixed", "area": "culture"},
    {"handle": "minitatu", "tier": 2, "bias": "mixed", "area": "culture"},
    {"handle": "zedigital", "tier": 2, "bias": "mixed", "area": "culture"},
    {"handle": "TimTursunov", "tier": 2, "bias": "mixed", "area": "culture"},
    {"handle": "Shorts456", "tier": 3, "bias": "mixed", "area": "culture"},
    {"handle": "video3601", "tier": 2, "bias": "mixed", "area": "culture"},
    {"handle": "hergonprime225", "tier": 3, "bias": "mixed", "area": "culture"},
    {"handle": "Video_ra", "tier": 2, "bias": "mixed", "area": "culture"},
    {"handle": "sokhryb", "tier": 2, "bias": "mixed", "area": "culture"},
    {"handle": "profilga_rasim_suratlar", "tier": 3, "bias": "mixed", "area": "culture"},
    {"handle": "lightroompresets_free", "tier": 3, "bias": "mixed", "area": "culture"},
    {"handle": "CentroMareeAvvisa", "tier": 3, "bias": "mixed", "area": "culture"},
    {"handle": "skphotoedits", "tier": 3, "bias": "mixed", "area": "culture"},
    {"handle": "py91m", "tier": 3, "bias": "mixed", "area": "culture"},
    {"handle": "photoloverr", "tier": 3, "bias": "mixed", "area": "culture"},
]
# Total: 1278 channels across 22+ areas (15 languages)
logger = logging.getLogger("openclaw.collector.telegram")

# Rate-limit settings to avoid Telegram flood-wait bans
_MAX_CONCURRENT = 5
_DELAY_BETWEEN_SECS = 0.5


class TelegramCollector(BaseCollector):
    """Collects messages from 483+ Telegram channels with rate limiting."""

    name = "telegram"
    requires_api_key = True

    async def collect(self) -> list[RawEvent]:
        if not TELEGRAM_API_ID or not TELEGRAM_API_HASH:
            self.logger.warning("Telegram credentials not configured, skipping")
            return []

        try:
            from telethon import TelegramClient
            from telethon.errors import FloodWaitError
        except ImportError:
            self.logger.error("telethon not installed, skipping Telegram collector")
            return []

        events: list[RawEvent] = []
        cutoff = datetime.now(timezone.utc) - timedelta(hours=1)
        semaphore = asyncio.Semaphore(_MAX_CONCURRENT)

        async with TelegramClient(
            "openclaw_session", int(TELEGRAM_API_ID), TELEGRAM_API_HASH
        ) as tg:
            async def _fetch_channel(channel_info: dict) -> list[RawEvent]:
                handle = channel_info["handle"]
                channel_events: list[RawEvent] = []
                async with semaphore:
                    try:
                        entity = await tg.get_entity(handle)
                        async for message in tg.iter_messages(entity, limit=20):
                            if message.date < cutoff:
                                break
                            text = message.text or ""
                            if not text or len(text) < 20:
                                continue
                            channel_events.append(self._make_event(
                                title=text[:120],
                                content=text,
                                url=f"https://t.me/{handle}/{message.id}",
                                published_at=message.date.replace(tzinfo=None),
                                raw_metadata={
                                    "channel": handle,
                                    "tier": channel_info["tier"],
                                    "bias": channel_info["bias"],
                                    "area": channel_info["area"],
                                    "message_id": message.id,
                                },
                            ))
                    except FloodWaitError as e:
                        self.logger.warning(
                            "Telegram flood-wait %ds on '@%s', stopping batch",
                            e.seconds, handle,
                        )
                        raise  # abort remaining channels this cycle
                    except Exception as e:
                        self.logger.warning(
                            "Telegram channel '@%s' failed: %s", handle, e
                        )
                    await asyncio.sleep(_DELAY_BETWEEN_SECS)
                return channel_events

            # Process channels sequentially with rate limiting
            for channel_info in TELEGRAM_CHANNELS:
                try:
                    result = await _fetch_channel(channel_info)
                    events.extend(result)
                except Exception:
                    # FloodWaitError — stop processing this cycle
                    break

        self.logger.info("Telegram collected %d messages", len(events))
        return events
