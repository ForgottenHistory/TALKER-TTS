-- bin/lua/infra/tts/tts_handler.lua
local http = require("infra.HTTP.HTTP")
local json = require("infra.HTTP.json")
local logger = require("framework.logger")

local tts_handler = {}

-- Helper functions to access MCM settings directly
local function is_tts_enabled()
    if ui_mcm then
        local enabled = ui_mcm.get("talker_tts/tts_enabled")
        if enabled == nil then return true end  -- Default to enabled
        return enabled
    end
    return true  -- Default to enabled if no MCM
end

local function get_tts_volume()
    if ui_mcm then
        local volume = ui_mcm.get("talker_tts/tts_volume")
        if volume == nil then return 75 end  -- Default volume
        return volume
    end
    return 75  -- Default volume if no MCM
end

-- Extract faction from speaker ID if possible
local function extract_faction_from_id(speaker_id)
    -- Try to get faction from game if possible
    local obj = level.object_by_id(tonumber(speaker_id))
    if obj and obj:section() then
        local section = obj:section()
        -- Map common sections to factions
        if string.find(section, "ecolog") then return "ecologist"
        elseif string.find(section, "dolg") then return "duty"
        elseif string.find(section, "freedom") then return "freedom"
        elseif string.find(section, "bandit") then return "bandit"
        elseif string.find(section, "army") then return "army"
        elseif string.find(section, "monolith") then return "monolith"
        elseif string.find(section, "merc") then return "mercenary"
        end
    end
    return "stalker"  -- Default fallback
end

function tts_handler.request_tts(speaker_id, dialogue, character_info, callback)
    logger.info("Requesting TTS for speaker %s: %s", speaker_id, dialogue)
    
    -- Check if TTS is enabled in MCM
    if not is_tts_enabled() then
        logger.info("TTS is disabled in MCM")
        callback(false)
        return
    end
    
    -- Get MCM volume setting
    local mcm_volume = get_tts_volume()  -- Returns 0-100
    logger.info("Using MCM volume: %d%%", mcm_volume)
    
    -- Handle missing character info with fallback
    local final_character_info = character_info
    if not character_info then
        logger.warn("No character info provided for speaker %s, creating fallback", speaker_id)
        final_character_info = {
            name = "Unknown Stalker",
            faction = extract_faction_from_id(speaker_id),
            personality = "neutral"
        }
    else
        -- Ensure required fields exist
        final_character_info = {
            personality = character_info.personality or "neutral",
            faction = character_info.faction or extract_faction_from_id(speaker_id),
            name = character_info.name or ("Stalker " .. speaker_id)
        }
    end
    
    logger.info("Using character info: %s", json.encode(final_character_info))
    
    -- Build request with MCM volume
    local request_data = {
        text = dialogue,
        character_info = final_character_info,
        mcm_volume = mcm_volume  -- Send MCM volume (0-100) to server
    }
    
    -- Send to local TTS service (API key is handled by server via .env file)
    local url = "http://127.0.0.1:8001/tts"
    local headers = {["Content-Type"] = "application/json"}
    
    logger.debug("Sending TTS request to server...")
    
    http.send_async_request(url, "POST", headers, request_data, function(resp, err)
        if err then
            logger.error("TTS request failed: %s", tostring(err))
            callback(false)
            return
        end
        
        -- Check for successful response
        if resp and resp.status == "playing" then
            logger.info("TTS audio playing through Windows: %s", resp.text or "")
            logger.info("Applied volume: %.2f", resp.applied_volume or 0)
            callback(true)  -- Return success, no audio file needed
        else
            logger.error("TTS response invalid: %s", json.encode(resp or {}))
            callback(false)
        end
    end)
end

return tts_handler