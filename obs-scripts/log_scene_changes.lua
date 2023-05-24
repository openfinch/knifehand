obs = obslua
last_scene_name = ""
log_file_path = os.getenv("HOME") .. "/" .. os.time() .. "-scene_changes.txt"

function script_description()
    return "This script logs scene changes to a file when OBS is live or recording."
end

function log_scene_change(scene_name, timestamp)
    local file, err = io.open(log_file_path, "a")
    if err then
        print("Failed to open " .. log_file_path .. " for writing")
    else
        file:write(timestamp .. ":" .. scene_name .. "\n")
        file:close()
    end
end

function on_event(event)
    print(event)
    if event == obs.OBS_FRONTEND_EVENT_STREAMING_STARTED or event == obs.OBS_FRONTEND_EVENT_RECORDING_STARTED then
        local scene = obs.obs_frontend_get_current_scene()
        local scene_name = obs.obs_source_get_name(scene)
        obs.obs_source_release(scene)
        last_scene_name = scene_name
        local timestamp = obs.obs_get_video_frame_time()  -- get the current time as the timestamp for starting streaming or recording
        log_scene_change(scene_name, timestamp)  -- log the initial scene
    end

    if event == obs.OBS_FRONTEND_EVENT_SCENE_CHANGED then
        local scene = obs.obs_frontend_get_current_scene()
        local scene_name = obs.obs_source_get_name(scene)
        obs.obs_source_release(scene)
        if scene_name ~= last_scene_name and (obs.obs_frontend_streaming_active() or obs.obs_frontend_recording_active()) then
            last_scene_name = scene_name
            local timestamp = obs.obs_get_video_frame_time()
            log_scene_change(scene_name, timestamp)
        end
    end
end

function script_load(settings)
    obs.obs_frontend_add_event_callback(on_event)
end
