"""Blueprint DSL for the crow agent. $Var -> getter, (set! Var x) -> setter (expanded by build_b.py)."""

A = "/Game/Characters/Crow/Animations/"
ANIM = {0: "AS_Crow_Idle", 1: "AS_Crow_Peck", 2: "AS_Crow_TakeOff", 3: "AS_Crow_Fly", 4: "AS_Crow_Glide", 5: "AS_Crow_Land"}
LOOP = {0: "true", 1: "false", 2: "false", 3: "true", 4: "true", 5: "false"}
_cases = "\n".join(
    f'      (:{i} (Components|Animation|PlayAnimation :self mesh :NewAnimToPlay "{A}{n}.{n}" :bLooping {LOOP[i]}))'
    for i, n in ANIM.items())

# ----------------------------------------------------------------- BODY: BP_CrowAgent
CROW_FUNCS = {
    # name: (params[(name, type, is_input)], dsl)
    "SetAnim": ([("Index", "int", True)], f"""
(fn SetAnim (Index)
  (if (!= Index $AnimState)
    (set! AnimState Index)
    (bind mesh $CrowMesh)
    (switch int Index
{_cases})))
"""),
    "ReturnToIdle": ([], """
(fn ReturnToIdle ()
  (if (== $Mode 0)
    (CallFunction|SetAnim :Index 0)))
"""),
    "FaceTowards": ([("Target", "Vector", True), ("DeltaSeconds", "float", True), ("Speed", "float", True)], """
(fn FaceTowards (Target DeltaSeconds Speed)
  (bind loc (Transformation|GetActorLocation))
  (bind look (Math|Rotator|FindLookatRotation loc Target))
  (bind cur (Transformation|GetActorRotation))
  (bind tgt (Math|Rotator|MakeRotator :Roll 0.0 :Pitch 0.0 :Yaw (.yaw look)))
  (Transformation|SetActorRotation :NewRotation (Math|Interpolation|RInterpTo cur tgt DeltaSeconds Speed)))
"""),
    "FlyStep": ([("Target", "Vector", True), ("DeltaSeconds", "float", True), ("Speed", "float", True)], """
(fn FlyStep (Target DeltaSeconds Speed)
  (bind loc (Transformation|GetActorLocation))
  (bind newloc (Math|Interpolation|VInterptoConstant loc Target DeltaSeconds Speed))
  (bind look (Math|Rotator|FindLookatRotation loc Target))
  (bind cur (Transformation|GetActorRotation))
  (bind tgt (Math|Rotator|MakeRotator :Roll 0.0 :Pitch (* (.pitch look) 0.5) :Yaw (.yaw look)))
  (Transformation|SetActorLocationAndRotation :NewLocation newloc :NewRotation (Math|Interpolation|RInterpTo cur tgt DeltaSeconds 4.0) :bSweep false :bTeleport false))
"""),
}

CROW_EVENTS = """
(event EventBeginPlay
  (set! AnimState -1)
  (bind loc (Transformation|GetActorLocation))
  (set! HomeLocation loc)
  (set! PerchLocation loc)
  (set! FlySpeed 650.0)
  (set! CircleRadius 550.0)
  (set! Mode 0)
  (set! PeckTimer (Math|Random|RandomFloatinRange 3.0 7.0))
  (CallFunction|SetAnim :Index 0))

(event Custom|FleeFrom
  (if (== $Mode 0)
    (bind loc (Transformation|GetActorLocation))
    (bind threat $ThreatLocation)
    (bind away (Math|Vector|Normalize (Math|Vector|MakeVector (- (.x loc) (.x threat)) (- (.y loc) (.y threat)) 0.0)))
    (bind endp (+ loc (+ (* away 260.0) (Math|Vector|MakeVector 0.0 0.0 230.0))))
    (bind center (+ loc (+ (* away 650.0) (Math|Vector|MakeVector 0.0 0.0 550.0))))
    (set! MoveStart loc)
    (set! MoveEnd endp)
    (set! MoveAlpha 0.0)
    (set! MoveDuration 0.73)
    (set! CircleCenter center)
    (set! CircleTime (Math|Random|RandomFloatinRange 5.0 9.0))
    (set! IsAlert false)
    (set! Mode 1)
    (CallFunction|SetAnim :Index 2)))

(event Custom|StartApproach
  (set! Mode 3)
  (set! IsGliding true)
  (CallFunction|SetAnim :Index 4))

(event EventTick (DeltaSeconds)
  (switch int $Mode
    (:0
      (if $IsAlert
        (CallFunction|FaceTowards :Target $LookTarget :DeltaSeconds DeltaSeconds :Speed 4.0))
      (set! PeckTimer (- $PeckTimer DeltaSeconds))
      (if (and (<= $PeckTimer 0.0) (== $AnimState 0))
        (set! PeckTimer (Math|Random|RandomFloatinRange 4.0 9.0))
        (if (not $IsAlert)
          (CallFunction|SetAnim :Index 1)
          (Utilities|Time|SetTimerbyFunctionName :Object self :FunctionName "ReturnToIdle" :Time 1.6 :bLooping false))))
    (:1
      (set! MoveAlpha (Math|Float|Min(Float) (+ $MoveAlpha (/ DeltaSeconds $MoveDuration)) 1.0))
      (bind a $MoveAlpha)
      (bind e (* (* a a) (- 3.0 (* 2.0 a))))
      (bind ms $MoveStart)
      (bind me $MoveEnd)
      (bind p (Math|Vector|Lerp(Vector) ms me e))
      (bind look (Math|Rotator|FindLookatRotation ms me))
      (bind face (Math|Rotator|MakeRotator :Roll 0.0 :Pitch 0.0 :Yaw (.yaw look)))
      (Transformation|SetActorLocationAndRotation :NewLocation p :NewRotation (Math|Interpolation|RInterpTo (Transformation|GetActorRotation) face DeltaSeconds 8.0) :bSweep false :bTeleport false)
      (if (>= a 1.0)
        (set! CircleAngle (.yaw (Math|Rotator|FindLookatRotation $CircleCenter p)))
        (set! GlideTimer (Math|Random|RandomFloatinRange 1.5 3.0))
        (set! IsGliding false)
        (set! Mode 2)
        (CallFunction|SetAnim :Index 3)))
    (:2
      (bind r $CircleRadius)
      (bind spd $FlySpeed)
      (set! CircleAngle (+ $CircleAngle (* DeltaSeconds (* (/ spd r) 57.2958))))
      (bind ang $CircleAngle)
      (bind tgt (+ $CircleCenter (Math|Vector|MakeVector (* (Math|Trig|Cos(Degrees) ang) r) (* (Math|Trig|Sin(Degrees) ang) r) 0.0)))
      (CallFunction|FlyStep :Target tgt :DeltaSeconds DeltaSeconds :Speed (* spd 1.2))
      (set! CircleTime (- $CircleTime DeltaSeconds))
      (set! GlideTimer (- $GlideTimer DeltaSeconds))
      (if (<= $GlideTimer 0.0)
        (set! IsGliding (not $IsGliding))
        (set! GlideTimer (Math|Random|RandomFloatinRange 1.5 3.0))
        (CallFunction|SetAnim :Index (select $IsGliding 4 3))))
    (:3
      (bind loc (Transformation|GetActorLocation))
      (bind perch $PerchLocation)
      (bind above (+ perch (Math|Vector|MakeVector 0.0 0.0 90.0)))
      (CallFunction|FlyStep :Target above :DeltaSeconds DeltaSeconds :Speed $FlySpeed)
      (if (< (Math|Vector|Distance(Vector) loc above) 380.0)
        (set! MoveStart loc)
        (set! MoveEnd perch)
        (set! LandElapsed 0.0)
        (set! Mode 4)
        (CallFunction|SetAnim :Index 5)))
    (:4
      (set! LandElapsed (+ $LandElapsed DeltaSeconds))
      (bind t $LandElapsed)
      (bind a (Math|Float|Min(Float) (/ t 0.75) 1.0))
      (bind inv (- 1.0 a))
      (bind e (- 1.0 (* inv inv)))
      (bind ms $MoveStart)
      (bind me $MoveEnd)
      (bind p (Math|Vector|Lerp(Vector) ms me e))
      (bind look (Math|Rotator|FindLookatRotation ms me))
      (bind face (Math|Rotator|MakeRotator :Roll 0.0 :Pitch 0.0 :Yaw (.yaw look)))
      (Transformation|SetActorLocationAndRotation :NewLocation p :NewRotation (Math|Interpolation|RInterpTo (Transformation|GetActorRotation) face DeltaSeconds 6.0) :bSweep false :bTeleport false)
      (if (>= t 1.1)
        (set! Mode 0)
        (set! IsAlert false)
        (set! PeckTimer (Math|Random|RandomFloatinRange 2.0 6.0))
        (CallFunction|SetAnim :Index 0)))))
"""

# ----------------------------------------------------------------- BRAIN: BP_CrowAIController
def _realm_case(k):
    return (f"    (:NewEnumerator{k}\n"
            f"      (set! RealmFlag (and (!= {k} $LastRealm) (>= $LastRealm 0)))\n"
            f"      (set! LastRealm {k})\n"
            f"      (return $RealmFlag))")

CTRL_FUNCS = {
    "RealmChanged": ([("Changed", "bool", False)], f"""
(fn RealmChanged ()
  (bind gm (Class|BFLGeneralFunctions|GetGameManager))
  (switch Utilities|FlowControl|Switch|SwitchonEnum_WorldRealm (Class|GIGameManager|GetWorldRealm gm)
{_realm_case(0)}
{_realm_case(1)}
{_realm_case(2)}))
"""),
    "ChoosePerch": ([("PlayerLoc", "Vector", True)], """
(fn ChoosePerch (PlayerLoc)
  (bind crow $Crow)
  (bind cloc (Transformation|GetActorLocation :self crow))
  (bind home (Class|BPCrowAgent|GetHomeLocation :self crow))
  (set! Found false)
  (set! BestDist 100000000.0)
  (set! BestLoc home)
  (if (> (Math|Vector|Distance(Vector) home PlayerLoc) $LandSafeRadius)
    (set! Found true)
    (set! BestDist (Math|Vector|Distance(Vector) home cloc)))
  (bind perches (Actor|GetAllActorsOfClass :ActorClass "/Game/Characters/Crow/Blueprints/BP_CrowPerch.BP_CrowPerch_C"))
  (for p perches
    (bind pl (Transformation|GetActorLocation :self p))
    (bind dc (Math|Vector|Distance(Vector) pl cloc))
    (if (and (> (Math|Vector|Distance(Vector) pl PlayerLoc) $LandSafeRadius) (< dc $BestDist))
      (set! BestDist dc)
      (set! BestLoc pl)
      (set! Found true)))
  (if $Found
    (Class|BPCrowAgent|SetPerchLocation :self crow :PerchLocation $BestLoc)
    (Class|BPCrowAgent|StartApproach :self crow)
    (else
      (Class|BPCrowAgent|SetCircleTime :self crow :CircleTime 2.0))))
"""),
}

CTRL_EVENTS = """
(event EventBeginPlay
  (set! AlertRadius 1100.0)
  (set! CalmFleeRadius 320.0)
  (set! RunFleeRadius 750.0)
  (set! RunSpeed 420.0)
  (set! LandSafeRadius 1000.0)
  (set! LastRealm -1))

(event EventOnPossess (PossessedPawn)
  (bind c (Utilities|Casting|CastToBP_CrowAgent :Object PossessedPawn)
    (:then
      (set! Crow c))
    (:CastFailed)))

(event EventTick (DeltaSeconds)
  (bind crow $Crow)
  (Utilities|IsValid crow
    (:"Is Valid"
      (bind player (Game|GetPlayerPawn 0))
      (bind ploc (Transformation|GetActorLocation :self player))
      (bind cloc (Transformation|GetActorLocation :self crow))
      (bind d (Math|Vector|Distance(Vector) ploc cloc))
      (bind speed (Math|Vector|VectorLength (Transformation|GetVelocity :self player)))
      (bind mode (Class|BPCrowAgent|GetMode :self crow))
      (bind changed (CallFunction|RealmChanged))
      (if changed
        (Class|BPCrowAgent|SetThreatLocation :self crow :ThreatLocation (- cloc (* (Transformation|GetActorForwardVector :self crow) 200.0)))
        (Class|BPCrowAgent|FleeFrom :self crow))
      (if (== mode 0)
        (Class|BPCrowAgent|SetIsAlert :self crow :IsAlert (< d $AlertRadius))
        (Class|BPCrowAgent|SetLookTarget :self crow :LookTarget ploc)
        (if (< d (select (> speed $RunSpeed) $RunFleeRadius $CalmFleeRadius))
          (Class|BPCrowAgent|SetThreatLocation :self crow :ThreatLocation ploc)
          (Class|BPCrowAgent|FleeFrom :self crow)))
      (if (and (== mode 2) (<= (Class|BPCrowAgent|GetCircleTime :self crow) 0.0))
        (CallFunction|ChoosePerch :PlayerLoc ploc)))
    (:"Is Not Valid")))
"""
