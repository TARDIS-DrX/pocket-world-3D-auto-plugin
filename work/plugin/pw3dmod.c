/* Pocket World 3D plugin v3
 *
 * ARM64 library loaded into the Houdini translated IL2CPP process.
 * Commands are executed on the Unity main thread through the
 * GameManager.Update MethodInfo pointer. If that dispatch is unavailable,
 * commands fall back to the attached worker thread.
 */

typedef unsigned long size_t;
typedef unsigned int uint32_t;
typedef struct FILE FILE;

extern void *dlopen(const char *filename, int flags);
extern void *dlsym(void *handle, const char *symbol);
extern FILE *fopen(const char *path, const char *mode);
extern int fclose(FILE *stream);
extern int fprintf(FILE *stream, const char *format, ...);
extern size_t fread(void *ptr, size_t size, size_t count, FILE *stream);
extern int usleep(unsigned int usec);
extern int mprotect(void *addr, size_t len, int prot);
extern int pthread_create(unsigned long *thread, const void *attr,
                          void *(*start_routine)(void *), void *arg);
extern int pthread_detach(unsigned long thread);

#define RTLD_NOW 2
#define PROT_RW 3
#define PROT_RWX 7

static const char *LOG_PATH =
    "/sdcard/Android/data/com.puzzle.miniworld.cn/files/pw3dmod.log";
static const char *TRIGGER_PATH =
    "/sdcard/Android/data/com.puzzle.miniworld.cn/files/auto.trigger";
static const char *CMD_PATH =
    "/sdcard/Android/data/com.puzzle.miniworld.cn/files/pw3d.cmd";
static const char *RESULT_PATH =
    "/sdcard/Android/data/com.puzzle.miniworld.cn/files/pw3d.result";
static const char *CFG_PATH =
    "/sdcard/Android/data/com.puzzle.miniworld.cn/files/pw3d.cfg";

static int g_page_size = 4096;

static void log_line(const char *message, void *a, void *b) {
    FILE *log = fopen(LOG_PATH, "a");
    if (log == 0) {
        return;
    }
    fprintf(log, "%s a=%p b=%p\n", message, a, b);
    fclose(log);
}

static void log_text(const char *tag, const char *text) {
    FILE *log = fopen(LOG_PATH, "a");
    if (log == 0) {
        return;
    }
    fprintf(log, "%s %s\n", tag, text);
    fclose(log);
}

static void write_result(const char *text) {
    FILE *out = fopen(RESULT_PATH, "w");
    if (out == 0) {
        return;
    }
    fprintf(out, "%s\n", text);
    fclose(out);
}

static int read_text_file(const char *path, char *buffer, int size) {
    FILE *in = fopen(path, "rb");
    size_t got;
    if (in == 0) {
        return -1;
    }
    got = fread(buffer, 1, (size_t)(size - 1), in);
    fclose(in);
    buffer[got] = 0;
    return (int)got;
}

static void clear_text_file(const char *path) {
    FILE *out = fopen(path, "w");
    if (out != 0) {
        fclose(out);
    }
}

static int text_same(const char *a, const char *b) {
    int i = 0;
    while (a[i] != 0 && b[i] != 0) {
        if (a[i] != b[i]) {
            return 0;
        }
        i++;
    }
    return a[i] == b[i];
}

static int text_starts(const char *s, const char *prefix) {
    int i = 0;
    while (prefix[i] != 0) {
        if (s[i] != prefix[i]) {
            return 0;
        }
        i++;
    }
    return 1;
}

static int parse_int(const char *s, int *out) {
    int sign = 1;
    int value = 0;
    int seen = 0;
    if (s == 0) {
        return 0;
    }
    if (*s == '-') {
        sign = -1;
        s++;
    } else if (*s == '+') {
        s++;
    }
    while (*s >= '0' && *s <= '9') {
        value = value * 10 + (*s - '0');
        seen = 1;
        s++;
    }
    if (!seen) {
        return 0;
    }
    *out = value * sign;
    return 1;
}

/* ------------------------------------------------------------------ */
/* IL2CPP API                                                          */

typedef void *(*fn_domain_get)(void);
typedef void **(*fn_get_assemblies)(void *domain, size_t *count);
typedef void *(*fn_assembly_get_image)(void *assembly);
typedef void *(*fn_class_from_name)(void *image, const char *ns, const char *name);
typedef void *(*fn_get_method)(void *klass, const char *name, int argc);
typedef void *(*fn_runtime_invoke)(void *method, void *obj, void **params, void **exc);
typedef void *(*fn_thread_attach)(void *domain);
typedef void *(*fn_class_get_type)(void *klass);
typedef void *(*fn_type_get_object)(void *type);
typedef void *(*fn_string_new)(const char *text);
typedef void *(*fn_field_from_name)(void *klass, const char *name);
typedef size_t (*fn_field_offset)(void *field);

static fn_get_assemblies g_get_assemblies;
static fn_assembly_get_image g_assembly_get_image;
static fn_class_from_name g_class_from_name;
static fn_get_method g_get_method;
static fn_runtime_invoke g_runtime_invoke;
static fn_class_get_type g_class_get_type;
static fn_type_get_object g_type_get_object;
static fn_string_new g_string_new;
static fn_field_from_name g_field_from_name;
static fn_field_offset g_field_offset;

static void **g_assemblies;
static size_t g_assembly_count;
static int g_api_ready;
static int g_ready;

static void *find_class_ns(const char *ns, const char *name) {
    size_t i;
    if (!g_api_ready) {
        return 0;
    }
    for (i = 0; i < g_assembly_count; i++) {
        void *image = g_assembly_get_image(g_assemblies[i]);
        void *klass;
        if (image == 0) {
            continue;
        }
        klass = g_class_from_name(image, ns, name);
        if (klass != 0) {
            return klass;
        }
    }
    return 0;
}

static void *find_class(const char *name) {
    return find_class_ns("", name);
}

static void *method_info(void *klass, const char *name, int argc) {
    if (klass == 0 || g_get_method == 0) {
        return 0;
    }
    return g_get_method(klass, name, argc);
}

static void *method_ptr(void *klass, const char *name, int argc) {
    void *info = method_info(klass, name, argc);
    if (info == 0) {
        return 0;
    }
    return *(void **)info;
}

static void fail_log(int stage, const char *text, void *a, void *b) {
    static int last_stage = -1;
    if (stage == last_stage) {
        return;
    }
    last_stage = stage;
    log_line(text, a, b);
}

static int api_init(void) {
    void *handle;
    fn_domain_get domain_get;
    fn_thread_attach attach;
    void *domain;

    if (g_ready) {
        return 1;
    }
    if (g_api_ready) {
        if (find_class("PlayerDataManager") == 0) {
            fail_log(5, "PlayerDataManager not found", (void *)g_assembly_count, 0);
            return 0;
        }
        g_ready = 1;
        log_line("il2cpp api ready", (void *)g_assembly_count, 0);
        return 1;
    }

    handle = dlopen("libil2cpp.so", RTLD_NOW);
    if (handle == 0) {
        fail_log(1, "dlopen libil2cpp failed", 0, 0);
        return 0;
    }
    domain_get = (fn_domain_get)dlsym(handle, "il2cpp_domain_get");
    g_get_assemblies = (fn_get_assemblies)dlsym(handle, "il2cpp_domain_get_assemblies");
    g_assembly_get_image =
        (fn_assembly_get_image)dlsym(handle, "il2cpp_assembly_get_image");
    g_class_from_name = (fn_class_from_name)dlsym(handle, "il2cpp_class_from_name");
    g_get_method = (fn_get_method)dlsym(handle, "il2cpp_class_get_method_from_name");
    g_runtime_invoke = (fn_runtime_invoke)dlsym(handle, "il2cpp_runtime_invoke");
    g_class_get_type = (fn_class_get_type)dlsym(handle, "il2cpp_class_get_type");
    g_type_get_object = (fn_type_get_object)dlsym(handle, "il2cpp_type_get_object");
    g_string_new = (fn_string_new)dlsym(handle, "il2cpp_string_new");
    g_field_from_name =
        (fn_field_from_name)dlsym(handle, "il2cpp_class_get_field_from_name");
    g_field_offset = (fn_field_offset)dlsym(handle, "il2cpp_field_get_offset");
    attach = (fn_thread_attach)dlsym(handle, "il2cpp_thread_attach");

    if (domain_get == 0 || g_get_assemblies == 0 || g_assembly_get_image == 0 ||
        g_class_from_name == 0 || g_get_method == 0 || g_runtime_invoke == 0 ||
        g_class_get_type == 0 || g_type_get_object == 0 || g_string_new == 0 ||
        g_field_from_name == 0 || g_field_offset == 0) {
        fail_log(2, "il2cpp symbol missing", domain_get, g_get_assemblies);
        return 0;
    }
    domain = domain_get();
    if (domain == 0) {
        fail_log(3, "il2cpp domain null", 0, 0);
        return 0;
    }
    if (attach != 0) {
        attach(domain);
    }
    g_assemblies = g_get_assemblies(domain, &g_assembly_count);
    if (g_assemblies == 0 || g_assembly_count == 0) {
        fail_log(4, "il2cpp assemblies empty", g_assemblies, (void *)g_assembly_count);
        return 0;
    }
    g_api_ready = 1;
    if (find_class("PlayerDataManager") == 0) {
        fail_log(5, "PlayerDataManager not found", (void *)g_assembly_count, 0);
        return 0;
    }
    g_ready = 1;
    log_line("il2cpp api ready", (void *)g_assembly_count, 0);
    return 1;
}

/* ------------------------------------------------------------------ */
/* main thread dispatch                                                */

static void *g_gm_orig;
static void *g_gm_method_info;
static volatile int g_main_tick;
static volatile int g_use_main;
static volatile int g_startup_flags;
static int g_maintain_tick;

static int g_vip_on;
static int g_ads_on;
static void save_cfg(void);

static void *player_instance(void) {
    void *klass = find_class("PlayerDataManager");
    void *fn = method_ptr(klass, "get_Instance", 0);
    if (fn == 0) {
        return 0;
    }
    return ((void *(*)(void *))fn)(0);
}

static void execute_pending(void);
static void free_apply(int on);
static void apply_vip(int on);
static void apply_ads(int on);
static void free_maintain(void);

static void gm_update(void *self) {
    g_main_tick++;
    if (g_startup_flags != 0) {
        int flags = g_startup_flags;
        g_startup_flags = 0;
        if ((flags & 4) != 0) {
            free_apply(1);
        }
        if ((flags & 1) != 0) {
            apply_vip(1);
        }
        if ((flags & 2) != 0) {
            apply_ads(1);
        }
    }
    execute_pending();
    g_maintain_tick++;
    if (g_maintain_tick >= 60) {
        g_maintain_tick = 0;
        free_maintain();
    }
    if (g_gm_orig != 0 && self != 0) {
        ((void (*)(void *, void *))g_gm_orig)(self, 0);
    }
}

static int install_main_dispatch(void) {
    void *klass = find_class("GameManager");
    void *info = method_info(klass, "Update", 0);
    unsigned long page;
    if (info == 0) {
        return 0;
    }
    g_gm_method_info = info;
    g_gm_orig = *(void **)info;
    page = (unsigned long)info & ~(unsigned long)(g_page_size - 1);
    if (mprotect((void *)page, (size_t)g_page_size, PROT_RW) != 0) {
        log_line("main dispatch mprotect failed", info, 0);
        g_gm_orig = 0;
        return 0;
    }
    *(void **)info = (void *)gm_update;
    __builtin___clear_cache((char *)info, (char *)info + 8);
    log_line("main dispatch installed", info, g_gm_orig);
    return 1;
}

static void restore_main_dispatch(void) {
    if (g_gm_method_info != 0 && g_gm_orig != 0) {
        *(void **)g_gm_method_info = g_gm_orig;
        log_line("main dispatch restored", g_gm_method_info, 0);
    }
}

/* ------------------------------------------------------------------ */
/* free currency                                                       */

static int g_free_on;
static int g_base_coin;
static int g_base_diamond;
static void *g_cost_patched_addr;
static unsigned int g_cost_orig;

static void disable_currency_sync(void) {
    void *manager_class = find_class("GoodItemsManager");
    void *get_instance = method_ptr(manager_class, "get_Instance", 0);
    void *manager;
    void *field;
    size_t offset;
    void *list;
    void *list_klass;
    void *remove;
    void *exc = 0;

    if (get_instance == 0) {
        return;
    }
    manager = ((void *(*)(void *))get_instance)(0);
    if (manager == 0) {
        return;
    }
    field = g_field_from_name(manager_class, "synGoodsList");
    if (field == 0) {
        return;
    }
    offset = g_field_offset(field);
    list = *(void **)((char *)manager + offset);
    if (list == 0) {
        return;
    }
    list_klass = *(void **)list;
    remove = method_ptr(list_klass, "Remove", 1);
    if (remove != 0) {
        ((int (*)(void *, int, void *))remove)(list, 1, 0); /* Diamond */
        ((int (*)(void *, int, void *))remove)(list, 2, 0); /* Coin */
    } else {
        void *clear = method_ptr(list_klass, "Clear", 0);
        if (clear != 0) {
            g_runtime_invoke((void *)clear, list, 0, &exc);
        }
    }
}

static void patch_free_cost(void) {
    void *klass = find_class("PlayerDataManager");
    void *cost = method_ptr(klass, "CostGoods", 5);
    unsigned int *code;
    int i;
    if (cost == 0 || g_cost_patched_addr != 0) {
        return;
    }
    code = (unsigned int *)cost;
    for (i = 0; i < 0x80; i++) {
        if (code[i] == 0x4B1502E1u && code[i + 1] == 0x2A1F03E0u) {
            unsigned long page = (unsigned long)&code[i] &
                                 ~(unsigned long)(g_page_size - 1);
            if (mprotect((void *)page, (size_t)g_page_size, PROT_RWX) != 0) {
                log_line("free cost mprotect failed", &code[i], 0);
                return;
            }
            g_cost_orig = code[i];
            code[i] = 0x2A1703E1u; /* mov w1, w23 */
            __builtin___clear_cache((char *)&code[i], (char *)&code[i] + 4);
            g_cost_patched_addr = &code[i];
            log_line("free cost patched", &code[i], 0);
            return;
        }
    }
    log_line("free cost signature missing", cost, 0);
}

static int get_goods(int type) {
    void *klass = find_class("PlayerDataManager");
    void *get = method_ptr(klass, "GetGoods", 1);
    void *instance = player_instance();
    if (get == 0 || instance == 0) {
        return 0;
    }
    return ((int (*)(void *, int, void *))get)(instance, type, 0);
}

static void set_goods(int type, int value) {
    void *klass = find_class("PlayerDataManager");
    void *set = method_ptr(klass, "SetGoods", 4);
    void *instance = player_instance();
    if (set == 0 || instance == 0) {
        return;
    }
    ((void (*)(void *, int, int, int, int, void *))set)(
        instance, type, value, 0, 0, 0);
}

static void free_maintain(void) {
    int coin;
    int diamond;
    if (!g_free_on) {
        return;
    }
    disable_currency_sync();
    coin = get_goods(2);
    if (coin < g_base_coin) {
        set_goods(2, g_base_coin);
    }
    diamond = get_goods(1);
    if (diamond < g_base_diamond) {
        set_goods(1, g_base_diamond);
    }
}

static void free_apply(int on) {
    g_free_on = on;
    if (on) {
        g_base_coin = get_goods(2);
        g_base_diamond = get_goods(1);
        disable_currency_sync();
        patch_free_cost();
        log_line("free currency on", (void *)(size_t)g_base_coin,
                 (void *)(size_t)g_base_diamond);
    } else {
        if (g_cost_patched_addr != 0) {
            unsigned long page = (unsigned long)g_cost_patched_addr &
                                 ~(unsigned long)(g_page_size - 1);
            if (mprotect((void *)page, (size_t)g_page_size, PROT_RWX) == 0) {
                *(unsigned int *)g_cost_patched_addr = g_cost_orig;
                __builtin___clear_cache((char *)g_cost_patched_addr,
                                         (char *)g_cost_patched_addr + 4);
            }
            g_cost_patched_addr = 0;
        }
        log_line("free currency off", 0, 0);
    }
}

/* ------------------------------------------------------------------ */
/* auto assemble                                                       */

static void *find_component_instance(const char *class_name) {
    void *object_class = find_class_ns("UnityEngine", "Object");
    void *target_class = find_class(class_name);
    void *find_info;
    void *params[2];
    void *exc = 0;
    void *array;
    unsigned int length;
    void **items;
    unsigned int i;
    unsigned char include_inactive = 1;

    if (object_class == 0 || target_class == 0) {
        return 0;
    }
    find_info = method_info(object_class, "FindObjectsOfType", 2);
    if (find_info == 0) {
        return 0;
    }
    params[0] = g_type_get_object(g_class_get_type(target_class));
    params[1] = &include_inactive;
    array = g_runtime_invoke(find_info, 0, params, &exc);
    if (exc != 0 || array == 0) {
        return 0;
    }
    length = *(unsigned int *)((char *)array + 0x18);
    items = (void **)((char *)array + 0x20);
    for (i = 0; i < length; i++) {
        if (items[i] != 0) {
            return items[i];
        }
    }
    return 0;
}

static void auto_start(void) {
    void *battle_class = find_class("battlePanel");
    void *panel = find_component_instance("battlePanel");
    void *puzzle_class = find_class("PuzzleManager");
    void *get_instance = method_ptr(puzzle_class, "get_Instance", 0);
    void *instance = 0;
    void *start = method_ptr(puzzle_class, "StartAutoFinishPuzzle", 0);

    if (get_instance != 0) {
        instance = ((void *(*)(void *))get_instance)(0);
    }
    if (panel == 0 || instance == 0 || start == 0) {
        write_result("error:enter a puzzle first");
        log_line("auto unavailable", panel, instance);
        return;
    }
    if (battle_class != 0) {
        void *field = g_field_from_name(battle_class, "autoPuzzleSpeed");
        if (field != 0) {
            size_t offset = g_field_offset(field);
            *(float *)((char *)panel + offset) = 0.3f;
            log_line("auto speed set", (void *)offset, 0);
        }
    }
    ((void (*)(void *, void *))start)(instance, 0);
    write_result("auto:started");
    log_line("auto started", instance, panel);
}

/* ------------------------------------------------------------------ */
/* ads and vip                                                         */

static void apply_vip(int on) {
    void *user_class = find_class("UserDataManager");
    void *user = 0;
    void *get_instance = method_ptr(user_class, "get_Instance", 0);
    void *set_int = method_ptr(user_class, "SetInt", 3);
    void *key;

    if (get_instance != 0) {
        user = ((void *(*)(void *))get_instance)(0);
    }
    if (user == 0 || set_int == 0) {
        write_result("error:vip api missing");
        log_line("vip api missing", user, set_int);
        return;
    }
    key = g_string_new("IsVipAndMonthCardPlayerKey");
    ((void (*)(void *, void *, int, int, void *))set_int)(user, key, on ? 1 : 0, 1, 0);

    if (on) {
        void *vip_class = find_class("VipDataManager");
        void *vip_get = method_ptr(vip_class, "get_Instance", 0);
        void *vip = vip_get == 0 ? 0 : ((void *(*)(void *))vip_get)(0);
        void *success = method_ptr(vip_class, "BuyMonthCardSuccess", 0);
        if (vip != 0 && success != 0) {
            ((void (*)(void *, void *))success)(vip, 0);
            log_line("month card success invoked", vip, 0);
        }
    }
    g_vip_on = on;
    save_cfg();
    write_result(on ? "vip:on" : "vip:off");
    log_line(on ? "vip on" : "vip off", user, 0);
}

static void apply_ads(int on) {
    void *player = player_instance();
    void *player_class = find_class("PlayerDataManager");
    void *set_remove = method_ptr(player_class, "SetBuyRemoveAdNum", 1);
    void *update_remove = method_ptr(player_class, "UpdateRemoveAdData", 0);

    if (player == 0 || set_remove == 0) {
        write_result("error:ads api missing");
        log_line("ads api missing", player, set_remove);
        return;
    }
    if (on) {
        if (update_remove != 0) {
            ((void (*)(void *, void *))update_remove)(player, 0);
        } else {
            ((void (*)(void *, int, void *))set_remove)(player, 1, 0);
        }
    } else {
        ((void (*)(void *, int, void *))set_remove)(player, 0, 0);
    }
    g_ads_on = on;
    save_cfg();
    write_result(on ? "ads:on" : "ads:off");
    log_line(on ? "ads on" : "ads off", player, 0);
}

/* ------------------------------------------------------------------ */
/* theme unlock                                                        */

static void unlock_current_theme(void) {
    void *object_class = find_class_ns("UnityEngine", "Object");
    void *kitpanel_class = find_class("KitInfoPanel");
    void *component_class = find_class_ns("UnityEngine", "Component");
    void *gameobject_class = find_class_ns("UnityEngine", "GameObject");
    void *find_info;
    void *get_gameobject;
    void *get_active;
    void *params[2];
    void *exc = 0;
    unsigned char include_inactive = 1;
    void *array;
    unsigned int length;
    void **items;
    unsigned int i;
    void *panel = 0;
    int kit = 0;
    void *player_klass;
    void *player;
    void *unlock;
    void *update;
    char text[40];
    int pos = 0;

    if (object_class == 0 || kitpanel_class == 0 || component_class == 0 ||
        gameobject_class == 0) {
        write_result("error:theme api missing");
        return;
    }
    find_info = method_info(object_class, "FindObjectsOfType", 2);
    get_gameobject = method_ptr(component_class, "get_gameObject", 0);
    get_active = method_ptr(gameobject_class, "get_activeInHierarchy", 0);
    if (find_info == 0 || get_gameobject == 0 || get_active == 0) {
        write_result("error:theme finder missing");
        return;
    }
    params[0] = g_type_get_object(g_class_get_type(kitpanel_class));
    params[1] = &include_inactive;
    array = g_runtime_invoke(find_info, 0, params, &exc);
    if (exc != 0 || array == 0) {
        write_result("error:theme scan failed");
        return;
    }
    length = *(unsigned int *)((char *)array + 0x18);
    items = (void **)((char *)array + 0x20);
    for (i = 0; i < length; i++) {
        void *candidate = items[i];
        void *gameobject;
        int active;
        if (candidate == 0) {
            continue;
        }
        gameobject = ((void *(*)(void *, void *))get_gameobject)(candidate, 0);
        if (gameobject == 0) {
            continue;
        }
        active = ((int (*)(void *, void *))get_active)(gameobject, 0);
        if (!active) {
            continue;
        }
        panel = candidate;
        break;
    }
    if (panel == 0) {
        write_result("error:open a theme page first");
        return;
    }
    {
        void *field = g_field_from_name(kitpanel_class, "kit");
        if (field == 0) {
            write_result("error:kit field missing");
            return;
        }
        kit = *(int *)((char *)panel + g_field_offset(field));
    }
    player_klass = find_class("PlayerDataManager");
    player = player_instance();
    unlock = method_ptr(player_klass, "UnLockKitLevelByKit", 1);
    update = method_ptr(player_klass, "UpdateLevelKitDataIsUnlock", 1);
    if (player == 0 || unlock == 0 || update == 0) {
        write_result("error:theme unlock api missing");
        return;
    }
    ((void (*)(void *, int, void *))unlock)(player, kit, 0);
    ((void (*)(void *, int, void *))update)(player, kit, 0);
    text[pos++] = 't';
    text[pos++] = 'h';
    text[pos++] = 'e';
    text[pos++] = 'm';
    text[pos++] = 'e';
    text[pos++] = ':';
    if (kit == 0) {
        text[pos++] = '0';
    } else {
        char digits[12];
        int count = 0;
        int value = kit;
        while (value > 0) {
            digits[count++] = (char)('0' + (value % 10));
            value /= 10;
        }
        while (count > 0) {
            text[pos++] = digits[--count];
        }
    }
    text[pos] = 0;
    write_result(text);
    log_text("theme ok", text);
}

/* ------------------------------------------------------------------ */
/* command queue                                                       */

enum {
    REQ_NONE = 0,
    REQ_AUTO = 1,
    REQ_ADS = 2,
    REQ_VIP = 3,
    REQ_THEME = 4,
    REQ_FREE = 5,
    REQ_STATUS = 6
};

static volatile int g_req_kind;
static volatile int g_req_value;

static void execute_pending(void) {
    int kind = g_req_kind;
    int value = g_req_value;
    if (kind == REQ_NONE) {
        return;
    }
    g_req_kind = REQ_NONE;
    if (kind == REQ_AUTO) {
        auto_start();
    } else if (kind == REQ_ADS) {
        apply_ads(value);
    } else if (kind == REQ_VIP) {
        apply_vip(value);
    } else if (kind == REQ_THEME) {
        unlock_current_theme();
    } else if (kind == REQ_FREE) {
        free_apply(value);
        write_result(value ? "free:on" : "free:off");
    } else if (kind == REQ_STATUS) {
        write_result(g_vip_on ? "status:vip=1" : "status:vip=0");
    }
}

/* ------------------------------------------------------------------ */
/* config                                                              */

static void save_cfg(void) {
    FILE *out = fopen(CFG_PATH, "w");
    if (out == 0) {
        return;
    }
    fprintf(out, "vip=%d\nads=%d\nfree=%d\n", g_vip_on, g_ads_on, g_free_on);
    fclose(out);
}

static void load_cfg(int *vip, int *ads, int *free_mode) {
    char buffer[80];
    int got;
    int i;
    *vip = 0;
    *ads = 0;
    *free_mode = 0;
    got = read_text_file(CFG_PATH, buffer, (int)sizeof(buffer));
    if (got <= 0) {
        return;
    }
    for (i = 0; i < got; i++) {
        if (i == 0 || buffer[i - 1] == '\n') {
            if (text_starts(buffer + i, "vip=1")) {
                *vip = 1;
            }
            if (text_starts(buffer + i, "ads=1")) {
                *ads = 1;
            }
            if (text_starts(buffer + i, "free=1")) {
                *free_mode = 1;
            }
        }
    }
}

/* ------------------------------------------------------------------ */
/* worker                                                              */

static void submit_line(const char *buffer) {
    if (text_same(buffer, "auto")) {
        g_req_kind = REQ_AUTO;
    } else if (text_starts(buffer, "ads:")) {
        g_req_value = buffer[4] == '1';
        g_req_kind = REQ_ADS;
    } else if (text_starts(buffer, "vip:")) {
        g_req_value = buffer[4] == '1';
        g_req_kind = REQ_VIP;
    } else if (text_same(buffer, "theme")) {
        g_req_kind = REQ_THEME;
    } else if (text_starts(buffer, "free:")) {
        g_req_value = buffer[5] == '1';
        g_req_kind = REQ_FREE;
    } else if (text_same(buffer, "status")) {
        g_req_kind = REQ_STATUS;
    }
}

static void read_command(void) {
    char buffer[64];
    int got = read_text_file(CMD_PATH, buffer, (int)sizeof(buffer));
    if (got < 0) {
        return;
    }
    clear_text_file(CMD_PATH);
    while (got > 0 &&
           (buffer[got - 1] == '\n' || buffer[got - 1] == '\r' ||
            buffer[got - 1] == ' ')) {
        got--;
    }
    buffer[got] = 0;
    if (got == 0) {
        return;
    }
    log_text("cmd", buffer);
    submit_line(buffer);
    if (!g_use_main) {
        execute_pending();
    }
}

static void *worker(void *arg) {
    int vip = 0;
    int ads = 0;
    int free_mode = 0;
    int settle = 0;
    (void)arg;
    usleep(4000000);
    for (;;) {
        if (!g_ready) {
            if (api_init()) {
                if (install_main_dispatch()) {
                    int waited = 0;
                    while (waited < 20 && g_main_tick == 0) {
                        usleep(100000);
                        waited++;
                    }
                    g_use_main = g_main_tick > 0;
                    if (!g_use_main) {
                        restore_main_dispatch();
                    }
                    log_line(g_use_main ? "main thread dispatch active"
                                        : "worker thread fallback",
                             (void *)(size_t)g_main_tick, 0);
                }
                load_cfg(&vip, &ads, &free_mode);
                g_startup_flags =
                    (vip ? 1 : 0) | (ads ? 2 : 0) | (free_mode ? 4 : 0);
                if (!g_use_main) {
                    if (free_mode) {
                        free_apply(1);
                    }
                    if (vip) {
                        apply_vip(1);
                    }
                    if (ads) {
                        apply_ads(1);
                    }
                    g_startup_flags = 0;
                }
                log_line("plugin ready", (void *)(size_t)vip, (void *)(size_t)free_mode);
            }
        } else {
            char trigger[16];
            if (read_text_file(TRIGGER_PATH, trigger, (int)sizeof(trigger)) > 0) {
                clear_text_file(TRIGGER_PATH);
                g_req_kind = REQ_AUTO;
                if (!g_use_main) {
                    execute_pending();
                }
            }
            read_command();
            settle++;
        }
        usleep(250000);
    }
    return 0;
}

__attribute__((constructor)) static void pw3dmod_init(void) {
    unsigned long thread = 0;
    log_line("pw3dmod v3 loaded", 0, 0);
    if (pthread_create(&thread, 0, worker, 0) == 0) {
        pthread_detach(thread);
    }
}
