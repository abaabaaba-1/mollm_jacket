import numpy as np
from pymoo.indicators.hv import HV
from pymoo.util.nds.non_dominated_sorting import NonDominatedSorting
from pymoo.util.ref_dirs import get_reference_directions
import pygmo as pg
import re

def extract_smiles_from_string(text):
    pattern = r"<candidate>(.*?)</candidate>"
    smiles_list = re.findall(pattern, text,flags=re.DOTALL)
    return smiles_list

def split_list(lst, n):
    """Splits the list lst into n nearly equal parts."""
    k, m = divmod(len(lst), n)
    return [lst[i*k + min(i, m):(i+1)*k + min(i+1, m)] for i in range(n)]


def fast_non_dominated_sort(population):
    S = [[] for _ in range(len(population))]
    front = [[]]
    n = [0 for _ in range(len(population))]
    rank = [0 for _ in range(len(population))]

    for p in range(len(population)):
        S[p] = []
        n[p] = 0
        for q in range(len(population)):
            if dominates(population[p], population[q]):
                S[p].append(q) 
            elif dominates(population[q], population[p]):
                n[p] += 1
        if n[p] == 0:
            rank[p] = 0
            front[0].append(p)
    
    i = 0
    while len(front[i]) != 0:
        Q = []
        for p in front[i]: # p: non dominated
            for q in S[p]:
                n[q] -= 1
                if n[q] == 0:
                    rank[q] = i + 1
                    Q.append(q)
        i = i + 1
        front.append(Q)

    del front[-1]
    return front

def dominates(ind1, ind2):
    not_worse_in_all = True
    strictly_better_in_one = False

    for x, y in zip(ind1.scores, ind2.scores):
        if x > y:
            not_worse_in_all = False
        if x < y:
            strictly_better_in_one = True

    return not_worse_in_all and strictly_better_in_one

def crowding_distance_assignment(front, population):
    distances = [0] * len(front)
    num_objectives = len(population[0].scores)
    
    for m in range(num_objectives):
        front.sort(key=lambda x: population[x].scores[m])
        distances[0] = distances[-1] = float('inf')
        for i in range(1, len(front) - 1):
            distances[i] += (population[front[i + 1]].scores[m] - population[front[i - 1]].scores[m]) / (max(population[k].scores[m] for k in front) - min(population[k].scores[m] for k in front)+1e-5)

    return distances

def nsga2_selection(population, pop_size,return_fronts=False):
    fronts = fast_non_dominated_sort(population)
    new_population = []
    for front in fronts:
        if len(new_population) + len(front) > pop_size:
            crowding_distances = crowding_distance_assignment(front, population)
            sorted_front = sorted(front, key=lambda x: crowding_distances[front.index(x)], reverse=True)
            new_population.extend(sorted_front[:pop_size - len(new_population)])
        else:
            new_population.extend(front)
    if return_fronts:
        return [population[i] for i in new_population],fronts
    return [population[i] for i in new_population]

def so_selection(population, pop_size):
    # Single objective
    sorted_items = sorted(population, key=lambda item: item.total, reverse=True)[:pop_size]
    return sorted_items

def nsga2_so_selection(population, pop_size):
    half_size = pop_size//2
    next_pops = so_selection(population,half_size)
    current_smis = [i.value for i in next_pops]
    fronts = fast_non_dominated_sort(population)
    for front in fronts:
        candidates = [population[i] for i in front]
        candidates = sorted(candidates, key=lambda item: item.total, reverse=True)
        for can in candidates:
            if len(next_pops) >= pop_size:
                assert len(next_pops) == pop_size
                return next_pops
            if can.value not in current_smis:
                next_pops.append(can)
                current_smis.append(can.value)
    return next_pops
            
def hvc_selection(pops,pop_size):
    scores = []
    for pop in pops:
        scores.append(pop.scores)
    scores = np.stack(scores)
    hv_pygmo = pg.hypervolume(scores)
    hvc = hv_pygmo.contributions(np.array([1.1 for i in range(scores.shape[1])]))
    sorted_indices = np.argsort(hvc)[::-1]  # Reverse to sort in descending order
    bestn = [pops[i] for i in sorted_indices[:pop_size]]
    return bestn


def top_auc(buffer, top_n, finish, freq_log, max_oracle_calls):
    sum = 0
    prev = 0
    called = 0
    ordered_results = list(sorted(buffer, key=lambda kv: kv[1], reverse=False))
    for idx in range(freq_log, min(len(buffer), max_oracle_calls), freq_log):
        temp_result = ordered_results[:idx]
        temp_result = list(sorted(temp_result, key=lambda kv: kv[0].total, reverse=True))[:top_n]
        top_n_now = np.mean([item[0].total for item in temp_result])
        sum += freq_log * (top_n_now + prev) / 2
        prev = top_n_now
        called = idx
    temp_result = list(sorted(ordered_results, key=lambda kv: kv[0].total, reverse=True))[:top_n]
    top_n_now = np.mean([item[0].total for item in temp_result])
    sum += (len(buffer) - called) * (top_n_now + prev) / 2
    if finish and len(buffer) < max_oracle_calls:
        sum += (max_oracle_calls - len(buffer)) * top_n_now
    return sum / max_oracle_calls

def cal_hv(scores):
    ref_point = np.array([1.1]*len(scores[0]))
    hv = HV(ref_point=ref_point)
    nds = NonDominatedSorting().do(scores,only_non_dominated_front=True)
    scores = scores[nds]
    return hv(scores)

def cal_fusion_hv(scores):
    ref_point = np.array([1.0,20.0])
    hv = HV(ref_point=ref_point)
    nds = NonDominatedSorting().do(scores,only_non_dominated_front=True)
    #scores = scores[nds]
    return hv(scores)



def _get_objective_matrix(population):
    """Convert a population of Items into an objective matrix for minimization."""
    if not population:
        return None
    try:
        F = np.array([ind.scores for ind in population], dtype=float)
    except Exception:
        return None
    if F.ndim != 2:
        return None
    if np.any(~np.isfinite(F)):
        return None
    return F


def _generate_reference_directions(n_obj, n_points):
    """Generate reference directions with a safe fallback."""
    try:
        # In current pymoo versions, the argument is `n_dim` instead of `n_obj`.
        ref_dirs = get_reference_directions("energy", n_dim=n_obj, n_points=n_points)
    except Exception:
        ref_dirs = get_reference_directions("das-dennis", n_dim=n_obj, n_points=n_points)
    ref_dirs = np.asarray(ref_dirs, dtype=float)
    # Normalise directions
    ref_dirs /= np.linalg.norm(ref_dirs, axis=1, keepdims=True) + 1e-12
    return ref_dirs


def _normalise_objectives(F):
    """Shift and scale objective matrix to [0, 1]-like range for each objective."""
    z_min = F.min(axis=0)
    F_shifted = F - z_min
    z_max = F_shifted.max(axis=0)
    z_max[z_max == 0.0] = 1.0
    F_norm = F_shifted / z_max
    return F_norm


def nsga3_selection(population, pop_size):
    """NSGA-III style environmental selection.

    This implementation follows the standard NSGA-III idea:
    - non-dominated sorting
    - fill fronts until the last front
    - for the last front, perform reference-direction based niching
    In degenerate or numerical edge cases, it falls back to nsga2_selection.
    """
    if not population:
        return []
    if len(population) <= pop_size:
        return population

    F = _get_objective_matrix(population)
    if F is None:
        return nsga2_selection(population, pop_size)

    # Degenerate: all individuals identical in objective space
    if np.allclose(F, F[0]):
        return nsga2_selection(population, pop_size)

    try:
        fronts = NonDominatedSorting().do(F, only_non_dominated_front=False)
    except Exception:
        return nsga2_selection(population, pop_size)

    N, n_obj = F.shape
    ref_dirs = _generate_reference_directions(n_obj, pop_size)
    F_norm = _normalise_objectives(F)

    selected = []  # indices in population

    for front in fronts:
        if len(selected) + len(front) < pop_size:
            selected.extend(front)
            continue

        # Need to choose K solutions from this last front using NSGA-III niching
        K = pop_size - len(selected)
        last_front = np.array(front, dtype=int)

        # Associate each solution in the last front with a reference direction
        F_last = F_norm[last_front]
        v_len = np.linalg.norm(F_last, axis=1, keepdims=True)
        v_len[v_len == 0.0] = 1e-12

        cosine = (F_last @ ref_dirs.T) / v_len
        cosine = np.clip(cosine, -1.0, 1.0)
        angles = np.arccos(cosine)

        assoc_dir = angles.argmin(axis=1)  # for each solution in last_front
        assoc_angle = angles[np.arange(len(last_front)), assoc_dir]
        d2 = np.sin(assoc_angle) * v_len.flatten()

        # Compute niche counts based on already selected individuals
        rho = np.zeros(ref_dirs.shape[0], dtype=int)
        if selected:
            F_sel = F_norm[selected]
            v_sel = np.linalg.norm(F_sel, axis=1, keepdims=True)
            v_sel[v_sel == 0.0] = 1e-12
            cosine_sel = (F_sel @ ref_dirs.T) / v_sel
            cosine_sel = np.clip(cosine_sel, -1.0, 1.0)
            angles_sel = np.arccos(cosine_sel)
            sel_dir = angles_sel.argmin(axis=1)
            for j in sel_dir:
                rho[j] += 1

        chosen_from_last = []
        available = np.ones(len(last_front), dtype=bool)

        while len(chosen_from_last) < K and np.any(available):
            # Feasible directions are those that still have available individuals
            feasible_dirs = []
            for j in range(ref_dirs.shape[0]):
                if np.any((assoc_dir == j) & available):
                    feasible_dirs.append(j)

            if not feasible_dirs:
                # Fallback: use NSGA-II crowding within the remaining of this front
                remaining_indices = last_front[available].tolist()
                if not remaining_indices:
                    break
                cd = crowding_distance_assignment(remaining_indices, population)
                sorted_front = sorted(
                    remaining_indices,
                    key=lambda x: cd[remaining_indices.index(x)],
                    reverse=True,
                )
                needed = K - len(chosen_from_last)
                chosen_from_last.extend(sorted_front[:needed])
                break

            # Pick the direction with the smallest niche count
            rho_min = min(rho[j] for j in feasible_dirs)
            cand_dirs = [j for j in feasible_dirs if rho[j] == rho_min]

            if len(cand_dirs) == 1:
                j_chosen = cand_dirs[0]
            else:
                j_chosen = cand_dirs[np.random.randint(len(cand_dirs))]

            # Among individuals associated with this direction, pick one with minimum d2
            cand_idx = [i for i in range(len(last_front)) if available[i] and assoc_dir[i] == j_chosen]
            if not cand_idx:
                # No more individuals in this direction; mark as saturated
                rho[j_chosen] = 10 ** 9
                continue

            best_local = min(cand_idx, key=lambda i: d2[i])
            chosen_from_last.append(last_front[best_local])
            available[best_local] = False
            rho[j_chosen] += 1

        selected.extend(chosen_from_last)
        break

    # Safety fallback if something went wrong
    if len(selected) < pop_size:
        return nsga2_selection(population, pop_size)

    return [population[i] for i in selected[:pop_size]]


def moeadd_selection(population, pop_size):
    """MOEA/DD-style environmental selection using decomposition.

    Simplified implementation:
    - generate reference (weight) vectors
    - for each vector, keep the solution with the best Tchebycheff aggregation
    - if not enough solutions are selected, fill the rest using NSGA-II selection
    """
    if not population:
        return []
    if len(population) <= pop_size:
        return population

    F = _get_objective_matrix(population)
    if F is None:
        return nsga2_selection(population, pop_size)

    N, n_obj = F.shape
    ref_dirs = _generate_reference_directions(n_obj, pop_size)

    # Tchebycheff decomposition (minimization)
    z = F.min(axis=0)
    F_shifted = F - z
    F_shifted[F_shifted < 0.0] = 0.0

    # g[i, j] = max_k w_jk * |f_ik - z_k|
    g = np.max(ref_dirs[None, :, :] * F_shifted[:, None, :], axis=2)  # (N, n_ref)

    # For each reference vector, pick the best individual
    best_per_vec = {}
    for idx, vec in enumerate(ref_dirs):
        best_idx = np.argmin(g[:, idx])
        best_per_vec[idx] = best_idx

    chosen = list(best_per_vec.values())

    if len(chosen) >= pop_size:
        # Too many; use NSGA-II on this subset to trim
        subpop = [population[i] for i in chosen]
        return nsga2_selection(subpop, pop_size)

    # Not enough: fill remaining slots using NSGA-II from the rest of the population
    remaining_indices = [i for i in range(N) if i not in chosen]
    remaining_pop = [population[i] for i in remaining_indices]

    if remaining_pop:
        extra_needed = pop_size - len(chosen)
        extra = nsga2_selection(remaining_pop, extra_needed)
        chosen_items = [population[i] for i in chosen] + extra
    else:
        chosen_items = [population[i] for i in chosen]

    return chosen_items[:pop_size]


def rvea_selection(population, pop_size):
    """RVEA-style environmental selection based on reference vectors and APD.

    Simplified single-generation RVEA:
    - normalise objectives
    - associate each solution to its nearest reference vector
    - within each reference vector, keep the solution with the smallest
      Angle Penalised Distance (APD)
    - if over-selected, trim by global APD; if under-selected, fill using NSGA-II
    """
    if not population:
        return []
    if len(population) <= pop_size:
        return population

    F = _get_objective_matrix(population)
    if F is None:
        return nsga2_selection(population, pop_size)

    N, n_obj = F.shape
    ref_dirs = _generate_reference_directions(n_obj, pop_size)
    F_norm = _normalise_objectives(F)

    # Pre-compute minimal inter-vector angle for each reference vector (gamma)
    dot_rr = np.clip(ref_dirs @ ref_dirs.T, -1.0, 1.0)
    angles_rr = np.arccos(dot_rr)
    np.fill_diagonal(angles_rr, np.inf)
    gamma = angles_rr.min(axis=1)
    gamma[~np.isfinite(gamma)] = 1.0

    alpha = 2.0  # penalty factor

    apd_list = []  # (idx, apd, dir)
    for i in range(N):
        v = F_norm[i]
        v_norm = np.linalg.norm(v)
        if not np.isfinite(v_norm) or v_norm == 0.0:
            continue
        cosines = np.clip(ref_dirs @ (v / v_norm), -1.0, 1.0)
        angles = np.arccos(cosines)
        j = int(angles.argmin())
        theta = angles[j]
        apd = (1.0 + alpha * theta / (gamma[j] + 1e-12)) * v_norm
        if np.isfinite(apd):
            apd_list.append((i, apd, j))

    if not apd_list:
        return nsga2_selection(population, pop_size)

    # For each reference direction, keep solution with smallest APD
    best_for_dir = {}
    for idx, apd, j in apd_list:
        if j not in best_for_dir or apd < best_for_dir[j][1]:
            best_for_dir[j] = (idx, apd)

    chosen_indices = [v[0] for v in best_for_dir.values()]

    if len(chosen_indices) > pop_size:
        # Too many: keep globally best APD
        chosen_pairs = sorted(best_for_dir.values(), key=lambda x: x[1])[:pop_size]
        chosen_indices = [idx for idx, _ in chosen_pairs]
    elif len(chosen_indices) < pop_size:
        # Not enough: fill using NSGA-II
        remaining_indices = [i for i in range(N) if i not in chosen_indices]
        remaining_pop = [population[i] for i in remaining_indices]
        if remaining_pop:
            extra_needed = pop_size - len(chosen_indices)
            extra = nsga2_selection(remaining_pop, extra_needed)
            chosen_items = [population[i] for i in chosen_indices] + extra
            return chosen_items[:pop_size]

    return [population[i] for i in chosen_indices[:pop_size]]
